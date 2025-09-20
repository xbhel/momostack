import logging
import os
import re
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable, Iterable, Iterator
from typing import Final, Literal, override

import ahocorasick  # type: ignore  # noqa: PGH003

from recognition.datamodels import Entity, EntityType, Segment
from recognition.patterns import patterns
from utils import io_util

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
    def extract(self, text: str) -> Iterable[Segment]:
        """Extract terms according to the configured nesting strategy."""
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
    def extract(self, text: str) -> Iterable[Segment]:
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


class RegexPatternExtractor(Extractor):
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

    def next(self, *extractors: Extractor) -> "ChainedExtractor":
        if not extractors:
            raise ValueError("Must provide at least one extractor.")
        # Create with first level extractors
        new_extractor = ChainedExtractor(*self._levels[0])
        new_extractor._levels = [*self._levels, extractors]
        return new_extractor

    @override
    def extract(self, text: str) -> list[Segment]:
        segments = [Segment(text, 0, len(text))]
        for extractors in self._levels:
            segments_list = self._process_level(segments, extractors)
            segments = self._flatten(segments_list)
        return segments

    def extract_with_tuple_result(self, text: str) -> tuple[list[Segment], ...]:
        segments = [Segment(text, 0, len(text))]

        for level in range(len(self._levels) - 1):
            segments_list = self._process_level(segments, self._levels[level])
            segments = self._flatten(segments_list)

        return tuple(self._process_level(segments, self._levels[-1]))

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
                    adjusted_segment = Segment(
                        extracted_segment.text,
                        extracted_segment.start + offset,
                        extracted_segment.end + offset,
                    )
                    next_segments.append(adjusted_segment)

            result.append(next_segments)

        return result

    def _flatten(self, segments_list: list[list[Segment]]) -> list[Segment]:
        return [segment for segments in segments_list for segment in segments]


_DATE_EXTRACTOR: Final = RegexPatternExtractor(patterns['date'])
_CASE_NO_EXTRACTOR: Final = RegexPatternExtractor(patterns['case_no'])
_ISSUE_NO_EXTRACTOR = RegexPatternExtractor(patterns['issue_nos'], True, 1)
_ARTICLE_NO_EXTRACTOR: Final = RegexPatternExtractor(patterns['article_no'])
_LAW_TITLE_EXTRACTOR = PairedSymbolExtractor(("《", "》"), False, "outermost", True)
_ABBR_DEFINITION_EXTRACTOR = RegexPatternExtractor(patterns['abbr_definition'], group=1)
_PAIRED_BRACKETS_EXTRACTOR: Final = RegexPatternExtractor(patterns['paired_brackets'])
_KEYWORD_MAPPING: dict[str, list[str]] = io_util.load_resource_json(
    "KeywordMapping.json"
)


def extract_entities(text: str) -> dict[EntityType, list[Entity]]:
    """
    Extracts all relevant entities from the input text, including those found via
    bracketed expressions, keyword-based extraction, and direct pattern matching.

    Returns a mapping from EntityType to a list of Entity objects.
    """
    # Extract entities within paired brackets (e.g., Issue No, Law Abbreviation)
    bracket_entity_map = _extract_bracketed_entities(text)

    # Extract entities by keywords, using abbreviations found in brackets as keywords
    abbr_entities = bracket_entity_map.pop(EntityType.LAW_ABBR, [])
    abbr_keywords = [entity.text for entity in abbr_entities]
    keywords = dict(_KEYWORD_MAPPING)
    keywords.setdefault(EntityType.LAW_ABBR.name, []).extend(abbr_keywords)
    keyword_entity_map = _extract_keyword_entities(text, keywords)

    # Extract entities using direct pattern-based extractors
    pattern_entity_map = _extract_pattern_entities(text)

    # Merge all entity mappings, giving precedence to later updates
    return {**pattern_entity_map, **bracket_entity_map, **keyword_entity_map}


def _extract_pattern_entities(text: str) -> dict[EntityType, list[Entity]]:
    """
    Extracts entities from the text using predefined pattern-based extractors.
    """
    entity_type_to_extractor: dict[EntityType, Extractor] = {
        EntityType.DATE: _DATE_EXTRACTOR,
        EntityType.CASE_NO: _CASE_NO_EXTRACTOR,
        EntityType.LAW_TITLE: _LAW_TITLE_EXTRACTOR,
        EntityType.LAW_ARTICLE_NO: _ARTICLE_NO_EXTRACTOR,
    }
    entities_by_type: dict[EntityType, list[Entity]] = defaultdict(list)

    for entity_type, extractor in entity_type_to_extractor.items():
        segments = extractor.extract(text)
        entities_by_type[entity_type] = [
            Entity.of(segment, entity_type) for segment in segments
        ]

    return entities_by_type


def _extract_bracketed_entities(text: str) -> dict[EntityType, list[Entity]]:
    """
    Extracts entities that are defined within paired brackets,
    such as Issue No and Law Abbreviation.
    """
    bracketed_type_to_extractor = {
        EntityType.ISSUE_NO: _ISSUE_NO_EXTRACTOR,
        EntityType.LAW_ABBR: _ABBR_DEFINITION_EXTRACTOR,
    }

    bracket_segments = _PAIRED_BRACKETS_EXTRACTOR.extract(text)
    entities_by_type: dict[EntityType, list[Entity]] = defaultdict(list)

    for bracket_segment in bracket_segments:
        offset = bracket_segment.start
        inner_text = bracket_segment.text

        for entity_type, extractor in bracketed_type_to_extractor.items():
            for entity in extractor.extract(inner_text):
                adjusted_entity = Entity(
                    text=entity.text,
                    start=entity.start + offset,
                    end=entity.end + offset,
                    entity_type=entity_type,
                )
                entities_by_type[entity_type].append(adjusted_entity)

    return entities_by_type


def _extract_keyword_entities(
    text: str, keywords_by_label: dict[str, list[str]]
) -> dict[EntityType, list[Entity]]:
    """
    Extracts entities from the text based on provided keyword mappings.
    The mapping should be from label (str) to a list of keywords (str).
    """
    # Build a reverse mapping from keyword to label
    keyword_to_label = {
        k: label for label, kws in keywords_by_label.items() for k in kws
    }
    extractor = KeywordExtractor(keywords=keyword_to_label.keys(), ignore_overlaps=True)
    found_segments = extractor.extract(text)

    entities_by_type: dict[EntityType, list[Entity]] = defaultdict(list)

    for segment in found_segments:
        label = keyword_to_label.get(segment.text)
        if label is None:
            raise ValueError(f"Unknown keyword: {segment.text}")

        entity_type_name = label.upper()
        if entity_type_name in EntityType.__members__:
            entity_type = EntityType[entity_type_name]
            entities_by_type[entity_type].append(Entity.of(segment, entity_type))
        else:
            logger.debug(
                f"Ignored entity with unknown type '{entity_type_name}': {segment}"
            )

    return entities_by_type
