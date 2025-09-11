import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable, Iterable
from typing import Literal

import ahocorasick  # type: ignore  # noqa: PGH003
from data_model import TextSpan


class Extractor(ABC):
    """
    Abstract base class for all extractors.
    """

    @abstractmethod
    def extract(self, text: str) -> Iterable[TextSpan]:
        """
        Extract entities from the given text.
        """
        raise NotImplementedError

    def _make_text_span(self, text: str, start: int, end: int) -> TextSpan:
        """
        Helper to create a TextSpan object.
        """
        return TextSpan(text, start, end)


class PairedSymbolExtractor(Extractor):
    """
    Extract entities enclosed within paired symbols (e.g., 《...》).

    Supports nested symbols with configurable extraction strategies:
      - "outermost": keep only the widest enclosing pair
      - "innermost": keep only the deepest enclosed pair
      - "all": keep all matched pairs

    If the outermost closing symbol is missing, the extractor can optionally
    fall back to using the widest (outermost) closed pair as the result.

    :param symbol_pair:
            A tuple of (left_symbol, right_symbol).
    :param include_symbols:
            Whether to include the enclosing symbols in the extracted value.
    :param strategy:
            Strategy for handling nested symbols ("outermost", "innermost", "all").
    :param allow_fallback_on_unclosed:
            If True, when the outermost pair is unclosed,
            the outermost closed pair will be used as a fallback
            (only in "outermost" mode).
    """

    def __init__(
        self,
        symbol_pair: tuple[str, str],
        include_symbols: bool = False,
        strategy: Literal["outermost", "innermost", "all"] = "all",
        allow_fallback_on_unclosed: bool = False,
    ):
        self._left, self._right = symbol_pair
        self._include_symbols = include_symbols
        self._extract_func = self._get_strategy_handler(strategy)
        self._allow_fallback_on_unclosed = allow_fallback_on_unclosed
        self._symbol_pattern = re.compile("|".join(re.escape(s) for s in symbol_pair))

    def extract(self, text: str) -> Iterable[TextSpan]:
        """Extract terms according to the configured nesting strategy."""
        yield from self._extract_func(text)

    def _extract_all(self, text: str) -> Iterable[TextSpan]:
        stack: deque[tuple[int, str]] = deque()
        for matcher in self._symbol_pattern.finditer(text):
            index, val = matcher.start(), matcher.group()
            # occur the left symbol
            if val == self._left:
                stack.append((index, val))
                continue
            # occur the right symbol
            if not stack or stack[-1][1] != self._left:
                continue

            left_index, _ = stack.pop()
            yield self._make_text_span(text, left_index, index + 1)

    def _extract_outermost(self, text: str) -> Iterable[TextSpan]:
        depth = 0
        stack: deque[tuple[int, str]] = deque()
        pending: dict[int, list[TextSpan]] = defaultdict(list)
        for matcher in self._symbol_pattern.finditer(text):
            index, val = matcher.start(), matcher.group()
            # left symbol
            if val == self._left:
                depth += 1
                stack.append((index, val))
                continue
            # right symbol
            if not stack or stack[-1][1] != self._left:
                continue

            left_index, _ = stack.pop()
            item = self._make_text_span(text, left_index, index + 1)
            if not stack:
                yield item
            else:
                pending[depth].append(item)
                pending.pop(depth + 1, None)
            depth -= 1

        # If there are closed inner pairs but an unmatched outer left remains,
        # optionally fall back to the widest (outermost) closed pair(s).
        if pending and self._allow_fallback_on_unclosed and depth > 0:
            outermost_level = min(pending.keys())
            yield from pending.pop(outermost_level)

        pending.clear()

    def _extract_innermost(self, text: str) -> Iterable[TextSpan]:
        depth = max_depth_seen = 0
        stack: deque[tuple[int, str]] = deque()
        for matcher in self._symbol_pattern.finditer(text):
            index, val = matcher.start(), matcher.group()

            # left symbol
            if val == self._left:
                depth += 1
                max_depth_seen = max(depth, max_depth_seen)
                stack.append((index, val))
                continue

            # right symbol
            if not stack or stack[-1][1] != self._left:
                continue

            left_index, _ = stack.pop()
            if depth == max_depth_seen:
                yield self._make_text_span(text, left_index, index + 1)

            depth -= 1
            if depth == 0:
                max_depth_seen = 0

    def _get_strategy_handler(
        self, strategy: str
    ) -> Callable[[str], Iterable[TextSpan]]:
        if strategy == "innermost":
            return self._extract_innermost
        if strategy == "outermost":
            return self._extract_outermost
        return self._extract_all

    def _make_text_span(self, text: str, start: int, end: int) -> TextSpan:
        if self._include_symbols:
            return TextSpan(text[start:end], start, end)

        inner_start = start + len(self._left)
        inner_end = end - len(self._right)
        return TextSpan(text[inner_start:inner_end], inner_start, inner_end)


class KeywordExtractor(Extractor):
    """
    Efficient multi-keyword extractor using Aho-Corasick automaton.

    Features:
    - Supports overlapping and non-overlapping (longest match) extraction.
    - Handles edge case where input is shorter than the longest keyword.
    - Returns TextSpan objects for each match.

    Args:
        keywords: Iterable of keywords to match.
        ignore_overlaps: If True, only the longest non-overlapping matches are returned.
    """

    def __init__(
        self,
        keywords: Iterable[str],
        ignore_overlaps: bool = False,
    ) -> None:
        self._ignore_overlaps = ignore_overlaps
        self._automaton = self._build_automaton(keywords)
        self._max_keyword_length = len(max(self._automaton.keys(), key=len))

    def extract(self, text: str) -> Iterable[TextSpan]:
        """
        Extract all keyword matches from the input text.

        :param text: Input string to search for keywords.
        :return: Iterable of TextSpan objects for each match.
        """
        padded_text = self._pad_text(text)
        if self._ignore_overlaps:
            iterator = self._automaton.iter_long(padded_text)
        else:
            iterator = self._automaton.iter(padded_text)
        for end_index, word in iterator:
            start = end_index - len(word) + 1
            end = end_index + 1
            if end > len(text):
                # Ignore matches that are only in the padding
                break
            yield self._make_text_span(word, start, end)

    def _build_automaton(self, keywords: Iterable[str]) -> ahocorasick.Automaton:
        automaton = ahocorasick.Automaton()
        for word in keywords:
            automaton.add_word(word, word)
        automaton.make_automaton()
        return automaton

    def _pad_text(self, text: str) -> str:
        """
        Pad the text with spaces if it's shorter than the longest keyword.
        This is a workaround for a known pyahocorasick bug.
        """
        # https://github.com/WojciechMula/pyahocorasick/issues/133
        if self._ignore_overlaps:
            padding_len = self._max_keyword_length - len(text)
            if padding_len > 0:
                return text + " " * padding_len
        return text
