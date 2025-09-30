import logging
import os
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable, Generator, Iterable, Iterator
from typing import Literal, override

import ahocorasick  # type: ignore  # noqa: PGH003

from linkgen.models import Segment
from linkgen.utils import coll_util

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"


logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))


class Extractor(ABC):
    """
    Abstract base class for all extractors.
    """

    @abstractmethod
    def extract(self, text: str) -> Iterable[Segment]:
        """
        Extract entities from the given text.
        """
        raise NotImplementedError

    def _make_value(self, text: str, start: int, end: int) -> Segment:
        """
        Helper to create a Segment object.
        """
        return Segment(text, start, end)


class PairedSymbolExtractor(Extractor):
    """
    Extract entities enclosed within paired symbols (e.g., 《...》).

    Supports nested symbols with configurable extraction strategies:
      - "outermost": keep only the widest enclosing pair
      - "innermost": keep only the deepest enclosed pair
      - "all": keep all matched pairs

    If the outermost closing symbol is missing, the extractor can optionally
    fall back to using the widest (outermost) closed pair as the result.

    Args:
        symbol_pair:
            A tuple of (left_symbol, right_symbol).
        include_symbols:
            Whether to include the enclosing symbols in the extracted value.
        strategy:
            Strategy for handling nested symbols ("outermost", "innermost", "all").
        allow_fallback_on_unclosed:
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

    @override
    def extract(self, text: str) -> Iterator[Segment]:
        """Extract segments according to the configured nesting strategy."""
        yield from self._extract_func(text)

    def _extract_all(self, text: str) -> Iterable[Segment]:
        stack: deque[tuple[int, str]] = deque()
        for matcher in self._symbol_pattern.finditer(text):
            index, val = matcher.start(), matcher.group()
            # left symbol
            if val == self._left:
                stack.append((index, val))
                continue
            # right symbol
            if not stack or stack[-1][1] != self._left:
                continue

            left_index, _ = stack.pop()
            yield self._make_value(text, left_index, index + 1)

    def _extract_outermost(self, text: str) -> Iterable[Segment]:
        depth = 0
        stack: deque[tuple[int, str]] = deque()
        pending: dict[int, list[Segment]] = defaultdict(list)
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
            item = self._make_value(text, left_index, index + 1)
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

    def _extract_innermost(self, text: str) -> Iterable[Segment]:
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
                yield self._make_value(text, left_index, index + 1)

            depth -= 1
            if depth == 0:
                max_depth_seen = 0

    def _get_strategy_handler(
        self, strategy: str
    ) -> Callable[[str], Iterable[Segment]]:
        if strategy == "innermost":
            return self._extract_innermost
        if strategy == "outermost":
            return self._extract_outermost
        return self._extract_all

    @override
    def _make_value(self, text: str, start: int, end: int) -> Segment:
        if self._include_symbols:
            return Segment(text[start:end], start, end)

        inner_start = start + len(self._left)
        inner_end = end - len(self._right)
        return Segment(text[inner_start:inner_end], inner_start, inner_end)


class KeywordExtractor(Extractor):
    """
    Efficient multi-keyword extractor using Aho-Corasick automaton.

    Features:
    - Supports overlapping and non-overlapping (longest match) extraction.
    - Handles edge case where input is shorter than the longest keyword.
    - Returns Segment objects for each match.

    Args:
        keywords: Iterable of keywords to match.
        ignore_overlaps: If True, only the longest non-overlapping matches are returned.

    Raises:
        ValueError: If keywords list is empty
    """

    def __init__(
        self,
        keywords: Iterable[str],
        ignore_overlaps: bool = False,
    ) -> None:
        self._ignore_overlaps = ignore_overlaps
        self._automaton = self._build_automaton(keywords)
        self._max_keyword_length = len(max(self._automaton.keys(), key=len))

    @override
    def extract(self, text: str) -> Iterator[Segment]:
        """
        Extract all keyword matches from the input text.
        Args:
            text: Input string to search for keywords.
        Returns:
            Iterable of Segment objects for each match.
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
            yield self._make_value(word, start, end)

    def _build_automaton(self, keywords: Iterable[str]) -> ahocorasick.Automaton:
        automaton = ahocorasick.Automaton()
        for word in keywords:
            automaton.add_word(word, word)

        if not automaton:
            raise ValueError("Failed to build automaton: empty keyword list.")

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


class PatternExtractor(Extractor):
    """
    Extract entities using regex patterns.

    Args:
        patterns: Single regex pattern or list of patterns to match.
        stop_on_first: If True, stop after first pattern finds matches.
        group: Which regex group to extract (0 for entire match).
    """

    def __init__(
        self,
        patterns: re.Pattern[str] | list[re.Pattern[str]],
        stop_on_first: bool = False,
        group: int = 0,
    ) -> None:
        super().__init__()
        self._group = group
        self._stop_on_first = stop_on_first
        self._patterns = patterns if isinstance(patterns, list) else [patterns]

    @override
    def extract(self, text: str) -> Iterator[Segment]:
        found_any = False
        for pattern in self._patterns:
            for matcher in pattern.finditer(text):
                found_any = True
                yield self._make_value(
                    matcher.group(self._group),
                    matcher.start(self._group),
                    matcher.end(self._group),
                )
            if self._stop_on_first and found_any:
                return


class ChainedExtractor(Extractor):
    """
    Chains multiple extractors to process text in hierarchical levels.

    Each level's extractors process the segments found by the previous level.
    """

    def __init__(self, *extractors: Extractor) -> None:
        if not extractors:
            raise ValueError("Must provide at least one extractor.")
        self._levels = [extractors]

    def then(self, *extractors: Extractor) -> "ChainedExtractor":
        if not extractors:
            raise ValueError("Must provide at least one extractor.")
        # Create with first level extractors
        new_extractor = ChainedExtractor(*self._levels[0])
        new_extractor._levels = [*self._levels, extractors]
        return new_extractor

    @override
    def extract(self, text: str) -> Iterator[Segment]:
        segments = iter([Segment(text, 0, len(text))])
        for extractors in self._levels:
            segments = self._process_level_lazy(segments, extractors)
        yield from segments

    def extract_with_tuple_result(self, text: str) -> tuple[list[Segment], ...]:
        segments = [Segment(text, 0, len(text))]

        for level in range(len(self._levels) - 1):
            segments_list = self._process_level(segments, self._levels[level])
            segments = coll_util.flatten(segments_list)

        return tuple(self._process_level(segments, self._levels[-1]))

    def _process_level_lazy(
        self, segments: Iterator[Segment], extractors: tuple[Extractor, ...]
    ) -> Generator[Segment, None, None]:
        for segment in segments:
            offset = segment.start
            for extractor in extractors:
                for extracted_segment in extractor.extract(segment.text):
                    # Adjust positions relative to original text
                    extracted_segment.start += offset
                    extracted_segment.end += offset
                    yield extracted_segment

    def _process_level(
        self, segments: list[Segment], extractors: tuple[Extractor, ...]
    ) -> list[list[Segment]]:
        result = []

        for extractor in extractors:
            next_segments: list[Segment] = []

            for segment in segments:
                offset = segment.start
                for extracted_segment in extractor.extract(segment.text):
                    # Adjust positions relative to original text
                    extracted_segment.start += offset
                    extracted_segment.end += offset
                    next_segments.append(extracted_segment)

            result.append(next_segments)

        return result


def resolve_overlaps[T: Segment](
    iterable: Iterable[T],
    strategy: Literal["longest", "earliest", "earliest_longest"],
    direct_only: bool = False,
) -> list[T]:
    """
    Resolve overlapping segments according to the specified strategy.

    This function processes a sequence of Segment objects and removes overlaps
    according to the chosen strategy. Optionally, you can restrict overlap
    handling to *direct* overlaps only.

    Args:
        iterable: An iterable of Segment objects.
        strategy: The overlap resolution strategy. One of:
            - "longest": For each group of overlapping segments, keep the longest.
            - "earliest": Keep the earliest non-overlapping segments.
            - "earliest_longest": Prefer earliest, break ties by longest.
        direct_only: If True, only directly overlapping segments are considered
                        conflicts; indirectly overlapping segments (via a chain of
                        overlaps) are treated as separate. Default is False.

    Returns:
        A list of resolved, non-overlapping Segment objects.

    Examples::

        # Suppose we have three segments: (0, 5), (4, 7), (6, 10)
        segments = [Segment(0, 5), Segment(4, 7), Segment(6, 10)]

        # Longest strategy, chained overlaps (direct_only=False)
        resolve_overlaps(segments, "longest", direct_only=False)

        # Output: [(0, 5)]  -> the overlapping chain (0-5,4-7,6-10) is merged,
        #           keeping the longest segment

        # Longest strategy, direct overlaps only (direct_only=True)
        resolve_overlaps(segments, "longest", direct_only=True)
        # Output: [(0, 5), (6, 10)] -> only direct overlaps are considered,
        #           so (0,5) and (4,7) are compared separately from (6,10)
    """
    match strategy:
        case "longest":
            segments = sorted(iterable, key=lambda x: x.start)
            func = _resolve_overlaps_keep_longest
        case "earliest":
            segments = sorted(iterable, key=lambda x: x.start)
            func = _resolve_overlaps_keep_earliest
        case "earliest_longest":
            segments = sorted(iterable, key=lambda x: (x.start, -x.end))
            func = _resolve_overlaps_keep_earliest

    if not segments:
        return []
    return func(segments, direct_only)


def _resolve_overlaps_keep_longest[T: Segment](
    segments: list[T], direct_only: bool = False
) -> list[T]:
    result = []
    longest = segments[0]
    group_end = longest.end

    for index in range(1, len(segments)):
        seg = segments[index]
        # Check if segments overlap: seg.start < group_end
        if seg.start < group_end:
            # Segments overlap, keep the longer one
            if (seg.end - seg.start) > (longest.end - longest.start):
                longest = seg
            group_end = longest.end if direct_only else max(group_end, seg.end)
        else:
            # No overlap, add the current longest to result and start new group
            result.append(longest)
            longest = seg
            group_end = longest.end

    # The last group
    result.append(longest)
    return result


def _resolve_overlaps_keep_earliest[T: Segment](
    segments: list[T], direct_only: bool = False
) -> list[T]:
    result = []
    prev_end = -1

    for segment in segments:
        if segment.start >= prev_end:
            result.append(segment)
            prev_end = segment.end
        if not direct_only:
            prev_end = max(prev_end, segment.end)
    return result
