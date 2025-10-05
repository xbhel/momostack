"""Tokenization utilities for parsing law titles.

This module exposes `LawTitleTokenizer`, a lightweight tokenizer that splits a
normalized law title string into three conceptual parts:

- prefixes: Promulgator keywords (e.g., issuing bodies) and any immediately
  following bracketed descriptions.
- core: The main title text excluding detected prefixes and trailing versions.
- suffixes: Trailing version information enclosed in brackets at the end of the
  string (potentially multiple consecutive bracket groups).

Index positions in returned `Token` objects always refer to the positions in
the fully normalized text after HTML entity unescaping, ASCII translation, and
whitespace removal.
"""

from collections.abc import Iterable
from itertools import chain
from typing import TYPE_CHECKING, Final, cast

from linkgen.config import patterns
from linkgen.helper import KeywordExtractor, PairedSymbolExtractor
from linkgen.models import Token, TokenSpan
from linkgen.utils import text_util

if TYPE_CHECKING:
    import re

_FORWARD_CHINESE: Final = "转发"
_NESTED_TITLE_PATTERN: Final = cast("re.Pattern[str]", patterns["nested_title"])


class LawTitleTokenizer:
    """Tokenizer for law titles.

    The tokenizer performs the following steps on input text before tokenizing:
    1) Unescape HTML entities
    2) Convert to ASCII where possible
    3) Remove all whitespaces

    After normalization, it extracts:
    - Prefix promulgators using a keyword extractor, along with adjacent bracket
      groups immediately following them.
    - Suffix versions by peeling off consecutive bracket groups from the end of
      the text.

    Args
    - promulgators: Iterable[str]
        A collection of promulgator keywords to detect at the beginning of the
        string. Overlaps are ignored in favor of longest non-overlapping
        matches.
    """

    _bracket_extractor = PairedSymbolExtractor(
        symbol_pair=("(", ")"),
        include_symbols=True,
        strategy="outermost",
        allow_fallback_on_unclosed=True,
    )

    def __init__(self, promulgators: Iterable[str]) -> None:
        """Initialize tokenizer with promulgator keywords.

        Raises
        - ValueError
            If the provided keyword list is empty (raised by the underlying
            `KeywordExtractor`).
        """
        self._promulgator_extractor = KeywordExtractor(
            promulgators, ignore_overlaps=True
        )

    def tokenize(self, text: str) -> TokenSpan:
        """Tokenize a law title into prefix tokens, core, and suffix tokens.

        Args
        - text: str
            Raw title text.

        Returns
        - TokenSpan
            Structured tokens including:
            - `normalized_text`: str of normalized input
            - `prefixes`: list[Token] detected at the start
            - `core`: Token representing main title text
            - `suffixes`: list[Token] trailing at the end

        Raises
        - ValueError
            If the input text is empty or only whitespace.
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        normalized_text = self._normalize_text(text)
        return self._extract_token_span(normalized_text)

    def _normalize_text(self, text: str) -> str:
        """Normalize the text."""
        text = text_util.unescape_html_entities(text)
        text = text_util.to_ascii(text)
        return text_util.remove_all_whitespaces(text)

    def _extract_token_span(self, text: str) -> TokenSpan:
        """Extract the base token span without nested handling."""
        start_idx, prefixes = self._extract_prefixes(text)
        end_idx, suffixes = self._extract_suffixes(text)

        # Guard against pathological ordering
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
        """Extract prefixes."""
        return self._extract_prefixes_promulgators(text)

    def _extract_suffixes(self, text: str) -> tuple[int, list[Token]]:
        """Extract suffixes."""
        return self._extract_suffixes_versions(text)

    def _extract_prefixes_promulgators(self, text: str) -> tuple[int, list[Token]]:
        """Extract prefix promulgators and any immediately following brackets.

        Walks forward from the beginning, consuming consecutive promulgator
        keywords. After each keyword, skips over any contiguous bracket group(s)
        and trailing commas. Stops when encountering a gap or non-matching text.
        """
        promulgators_it = self._promulgator_extractor.extract(text)
        promulgators = sorted(promulgators_it, key=lambda x: x.start)
        if not promulgators:
            return 0, []

        start_idx = 0
        brackets = self._bracket_extractor.extract(text)
        start_idx_lookup = {x.start: x for x in brackets}

        for item in promulgators:
            # Discontinuous promulgators(e.g. A,xxx,B)
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

    def _extract_suffixes_versions(self, text: str) -> tuple[int, list[Token]]:
        """Extract trailing bracket groups as versions.

        Iteratively peels off consecutive bracket groups from the end of the
        text. Only bracket groups that form a contiguous suffix are considered
        versions.
        """
        if not text.endswith(")"):
            return len(text), []

        end_idx = len(text)
        brackets = self._bracket_extractor.extract(text)
        end_idx_lookup = {x.end: x for x in brackets}

        trailing: list[Token] = []
        # Remove brackets from the end, working backwards, collecting them
        while bracket := end_idx_lookup.get(end_idx):
            trailing.append(bracket)
            end_idx = bracket.start

        # Order suffix groups from left to right appearance
        trailing.sort(key=lambda s: s.start)
        return end_idx, trailing


class NestedLawTitleTokenizer(LawTitleTokenizer):
    """Tokenizer for nested law titles.

    Extends `LawTitleTokenizer` by additionally detecting a nested law title
    pattern inside the normalized text (when present and not a forwarded
    document). When a nested title is detected, its tokens are extracted and
    merged with the base tokens. The resulting `TokenSpan` marks `nested=True`
    and preserves both the outer normalized text and the nested normalized
    text.
    """

    def __init__(self, promulgators: Iterable[str]) -> None:
        """Initialize nested tokenizer with promulgator keywords."""
        super().__init__(promulgators)

    def _extract_token_span(self, text: str) -> TokenSpan:
        """Extract tokens and merge nested title tokens when applicable."""
        base_span = super()._extract_token_span(text)
        nested_span = self._extract_nested_token_span(text)
        if nested_span:
            return self._merge_token_span(base_span, nested_span)
        return base_span

    def _extract_nested_token_span(self, text: str) -> TokenSpan | None:
        """Extract a nested `TokenSpan` if the text contains a nested title.

        Returns None when the content appears to be a forward (contains
        "转发") or no nested title pattern is matched.
        """
        if text.find(_FORWARD_CHINESE) != -1 or not (
            matcher := _NESTED_TITLE_PATTERN.match(text)
        ):
            return None

        offset, nested_text = matcher.start(1), matcher.group(1)
        nested_token_span = super()._extract_token_span(nested_text)
        self._update_nested_token_span_offset(nested_token_span, offset)
        return nested_token_span

    def _update_nested_token_span_offset(
        self, token_span: TokenSpan, offset: int
    ) -> None:
        """Shift all token offsets in a `TokenSpan` by a constant amount."""
        self._update_token_offset(token_span.core, offset)
        for token in chain(token_span.prefixes, token_span.suffixes):
            self._update_token_offset(token, offset)

    @staticmethod
    def _merge_token_span(
        token_span: TokenSpan, nested_token_span: TokenSpan
    ) -> TokenSpan:
        """Merge base and nested token spans into a single result."""
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

    @staticmethod
    def _update_token_offset(token: Token, offset: int) -> None:
        token.start += offset
        token.end += offset


class StrictLawTitleTokenizer(LawTitleTokenizer):
    """Tokenizer for strict law titles.

    Currently identical to `LawTitleTokenizer`. Reserved for stricter
    validation or rule enforcement in the future.
    """

    def _extract_nested_text(self, text: str) -> str:
        """Placeholder hook for strict nested text extraction."""
        return text
