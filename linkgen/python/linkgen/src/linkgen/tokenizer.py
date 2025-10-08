"""Tokenization utilities for parsing law titles.

This module provides a flexible tokenization system for law titles with support for:
- Basic law title tokenization (prefixes, core, suffixes)
- Nested law title detection and processing
- Strict validation with pattern-based suffix filtering
- Extensible architecture for custom tokenization rules

The tokenizer normalizes input text through HTML entity unescaping, ASCII conversion,
and whitespace removal before extracting structured tokens.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from itertools import chain
from typing import TYPE_CHECKING, Final, cast, override

from linkgen.config import patterns
from linkgen.helper import KeywordExtractor, PairedSymbolExtractor
from linkgen.models import Token, TokenSpan
from linkgen.utils import text_util

if TYPE_CHECKING:
    import re
    from collections.abc import Iterable

_FORWARD_CHINESE: Final = "转发"


class BaseTokenizer(ABC):
    """Abstract base class for law title tokenizers."""

    @abstractmethod
    def tokenize(self, text: str) -> TokenSpan:
        """Tokenize a law title into structured tokens.

        Args:
            text: Raw title text to tokenize.

        Returns:
            TokenSpan containing structured tokens.

        Raises:
            ValueError: If the input text is empty or only whitespace.
        """
        raise NotImplementedError("Subclasses must implement tokenize method")


class LawTitleTokenizer(BaseTokenizer):
    """Standard tokenizer for law titles.

    Performs text normalization and extracts:
    - Prefix promulgators with adjacent bracket groups
    - Core title text
    - Suffix version information from trailing brackets

    The tokenizer uses a keyword extractor for promulgators and a paired symbol
    extractor for bracket groups.

    Example::

        tokenizer = LawTitleTokenizer(['中华人民共和国', '最高人民法院'])
        result = tokenizer.tokenize("中华人民共和国民法典(2020年)")
        # result: TokenSpan(
        #     normalized_text="中华人民共和国民法典(2020年)",
        #     prefixes=[Token(text="中华人民共和国", start=0, end=5)],
        #     core=Token(text="民法典", start=5, end=10),
        #     suffixes=[Token(text="(2020年)", start=10, end=16)]
        # )
    """

    _bracket_extractor = PairedSymbolExtractor(
        symbol_pair=("(", ")"),
        include_symbols=True,
        strategy="outermost",
        allow_fallback_on_unclosed=True,
    )

    def __init__(self, promulgators: Iterable[str]) -> None:
        """Initialize tokenizer with promulgator keywords.

        Args:
            promulgators: Collection of promulgator keywords to detect.

        Raises:
            ValueError: If the provided keyword list is empty.
        """
        self._promulgator_extractor = KeywordExtractor(
            promulgators, ignore_overlaps=True
        )

    def tokenize(self, text: str) -> TokenSpan:
        """Tokenize a law title into prefix tokens, core, and suffix tokens.

        Args:
            text: Raw title text to tokenize.

        Returns:
            TokenSpan containing structured tokens:
            - `normalized_text`: Normalized input text
            - `prefixes`: List of tokens detected at the start
            - `core`: Token representing main title text
            - `suffixes`: List of tokens trailing at the end

        Raises:
            ValueError: If the input text is empty or only whitespace.
            TypeError: If the input is not a string.
        """
        self._validate_input(text)
        normalized_text = self._normalize_text(text)
        return self._extract_token_span(normalized_text)

    def _validate_input(self, text: str) -> None:
        """Validate input text for tokenization.

        Args:
            text: Text to validate.

        Raises:
            ValueError: If the input text is empty or only whitespace.
            TypeError: If the input is not a string.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

    def _normalize_text(self, text: str) -> str:
        """Normalize the input text through a series of transformations.

        Args:
            text: Raw text to normalize.

        Returns:
            Normalized text after HTML entity unescaping, ASCII conversion,
            and whitespace removal.
        """
        text = text_util.unescape_html_entities(text)
        text = text_util.to_ascii(text)
        return text_util.remove_all_whitespaces(text)

    def _extract_token_span(self, text: str) -> TokenSpan:
        """Extract the base token span without nested handling.

        Args:
            text: Normalized text to extract tokens from.

        Returns:
            TokenSpan with extracted prefixes, core, and suffixes.
        """
        start_idx, prefixes = self._extract_prefixes(text)
        end_idx, suffixes = self._extract_suffixes(text)

        # Guard against pathological ordering - ensure valid core bounds
        if start_idx >= end_idx:
            start_idx = 0
            end_idx = len(text)

        return TokenSpan(
            normalized_text=text,
            prefixes=prefixes,
            suffixes=suffixes,
            core=Token(text[start_idx:end_idx], start_idx, end_idx),
        )

    def _extract_prefixes(self, text: str) -> tuple[int, list[Token]]:
        """Extract prefix promulgators and any immediately following brackets.

        Walks forward from the beginning, consuming consecutive promulgator
        keywords. After each keyword, skips over any contiguous bracket group(s)
        and trailing commas. Stops when encountering a gap or non-matching text.

        Args:
            text: Normalized text to extract prefixes from.

        Returns:
            Tuple of (core_start_index, list_of_prefix_tokens).
        """
        promulgators_it = self._promulgator_extractor.extract(text)
        promulgators = sorted(promulgators_it, key=lambda x: x.start)
        if not promulgators:
            return 0, []

        start_idx = 0
        brackets = self._bracket_extractor.extract(text)
        start_idx_lookup = {x.start: x for x in brackets}

        for item in promulgators:
            # Discontinuous promulgators (e.g. A,xxx,B)
            if item.start > start_idx:
                break
            # It is a part of the description of the previous promulgator
            # e.g. A(B)
            if item.start < start_idx:
                continue

            start_idx = item.end
            # Move past any immediately following brackets
            while bracket := start_idx_lookup.get(start_idx):
                start_idx = bracket.end
            # Skip trailing commas
            while start_idx < len(text) and text[start_idx] == ",":
                start_idx += 1

        return start_idx, [x for x in promulgators if x.end <= start_idx]

    def _extract_suffixes(self, text: str) -> tuple[int, list[Token]]:
        """Extract trailing bracket groups as versions.

        Iteratively peels off consecutive bracket groups from the end of the
        text. Only bracket groups that form a contiguous suffix are considered
        versions.

        Args:
            text: Normalized text to extract suffixes from.

        Returns:
            Tuple of (core_end_index, list_of_suffix_tokens).
        """
        if not text.endswith(")"):
            return len(text), []

        end_idx = len(text)
        brackets = self._bracket_extractor.extract(text)
        end_idx_lookup = {x.end: x for x in brackets}

        trailing: list[Token] = []
        # Remove brackets from the end, working backwards, collecting them
        while bracket := end_idx_lookup.get(end_idx):
            if not self._is_valid_suffix(bracket):
                break
            trailing.append(bracket)
            end_idx = bracket.start

        # Order suffix groups from left to right appearance
        trailing.sort(key=lambda s: s.start)
        return end_idx, trailing

    def _is_valid_suffix(self, suffix: Token) -> bool:  # noqa: ARG002
        """Check if a version token is valid.

        Args:
            suffix: Token to validate.

        Returns:
            True if the suffix is valid, False otherwise.
        """
        return True  # Base implementation accepts all versions


class NestedLawTitleTokenizer(LawTitleTokenizer):
    """Tokenizer for nested law titles.

    Extends `LawTitleTokenizer` by detecting nested law title patterns within
    the normalized text. When a nested title is found (and not a forwarded
    document), its tokens are extracted and merged with the base tokens.

    The resulting `TokenSpan` marks `nested=True` and preserves both the outer
    and nested normalized text.

     Example::

        tokenizer = NestedLawTitleTokenizer(['中华人民共和国', '最高人民法院'])
        result = tokenizer.tokenize("中华人民共和国民法典(2020年)")
        # result: TokenSpan(
        #     normalized_text="中华人民共和国民法典(2020年)",
        #     prefixes=[Token(text="中华人民共和国", start=0, end=5)],
        #     core=Token(text="民法典", start=5, end=10),
        #     suffixes=[Token(text="(2020年)", start=10, end=16)]
        # )

        result = tokenizer.tokenize(
            "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定(一)")
        # result: TokenSpan(
        #     normalized_text=
        #           "最高人民法院关于适用<中华人民共和国公司法>若干问题的规定(一)",
        #     nested_text="中华人民共和国公司法",
        #     prefixes=[Token(text='最高人民法院', start=0, end=6),
        #                Token(text='中华人民共和国', start=11, end=18)],
        #     core=Token(text="公司法", start=18, end=21),
        #     suffixes=[Token(text="(一)", start=29, end=32)]
        # )
    """

    _nested_title_pattern = cast("re.Pattern[str]", patterns["nested_title"])
    _suffixes_pattern = cast("list[re.Pattern[str]]", patterns["title_suffixes"])

    def __init__(self, promulgators: Iterable[str], strict: bool = False) -> None:
        super().__init__(promulgators)
        self._strict = strict

    def _extract_token_span(self, text: str) -> TokenSpan:
        base_span = super()._extract_token_span(text)

        if nested_span := self._extract_nested_token_span(text, base_span):
            return self._merge_token_span(base_span, nested_span)

        return base_span

    def _extract_nested_token_span(
        self, text: str, base_span: TokenSpan
    ) -> TokenSpan | None:
        """Extract a nested `TokenSpan` if the text contains a nested title."""
        offset, nested_text = self._extract_nested_text(text, base_span)
        if nested_text is None:
            return None

        token_span = super()._extract_token_span(nested_text)
        self._update_token_span_offset(token_span, offset)
        return token_span

    @override
    def _is_valid_suffix(self, version: Token) -> bool:
        """Check if a version token is valid using strict pattern matching.

        Args:
            version: Token to validate.

        Returns:
            True if the version is valid, False otherwise.
        """
        if self._strict:
            return any(
                pattern.match(version.text) for pattern in self._suffixes_pattern
            )
        return True

    def _extract_nested_text(
        self, text: str, base_span: TokenSpan
    ) -> tuple[int, str | None]:
        """Extract nested text from the input if it matches the nested pattern.

        Args:
            text: Original normalized text.
            base_span: Base token span for additional validation.

        Returns:
            Tuple of (offset, nested_text) or (-1, None) if no match.
        """
        # Skip if text contains forward marker or no pattern match
        if text.find(_FORWARD_CHINESE) != -1 or (
            (matcher := self._nested_title_pattern.match(text)) is None
        ):
            return -1, None

        # Additional strict validation for core text format
        start, end = base_span.core.start, base_span.core.end
        if self._strict and (text[start] != "<" or text[end - 1] != ">"):
            return -1, None

        return matcher.start(1), matcher.group(1)

    def _update_token_span_offset(self, token_span: TokenSpan, offset: int) -> None:
        """Shift all token offsets in a `TokenSpan` by a constant amount.

        Args:
            token_span: The TokenSpan to update.
            offset: The amount to shift all token positions by.
        """
        for token in chain(
            [token_span.core],
            token_span.prefixes,
            token_span.suffixes,
        ):
            token.start += offset
            token.end += offset

    @staticmethod
    def _merge_token_span(
        token_span: TokenSpan, nested_token_span: TokenSpan
    ) -> TokenSpan:
        """Merge base and nested token spans into a single result.

        Args:
            token_span: The base token span.
            nested_token_span: The nested token span to merge.

        Returns:
            Merged TokenSpan with combined prefixes and suffixes.
        """
        prefixes = sorted(
            token_span.prefixes + nested_token_span.prefixes,
            key=lambda x: x.start,
        )
        suffixes = sorted(
            token_span.suffixes + nested_token_span.suffixes,
            key=lambda x: x.start,
        )
        return TokenSpan(
            nested=True,
            prefixes=prefixes,
            suffixes=suffixes,
            core=nested_token_span.core,
            normalized_text=token_span.normalized_text,
            nested_text=nested_token_span.normalized_text,
        )
