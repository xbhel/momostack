import logging
import os
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable, Generator, Iterable, Iterator
from itertools import chain
from typing import Any, Final, Literal, override

import ahocorasick  # type: ignore  # noqa: PGH003

from recognition.datamodels import Entity, EntityType, Segment
from recognition.patterns import patterns
from recognition.resolver import resolve_overlaps
from utils import io_util, text_util

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


_DATE_EXTRACTOR: Final = PatternExtractor(patterns["date"])
_CASE_NO_EXTRACTOR: Final = PatternExtractor(patterns["case_no"])
_ISSUE_NO_EXTRACTOR = PatternExtractor(patterns["issue_nos"], True, 1)
_ARTICLE_NO_EXTRACTOR: Final = PatternExtractor(patterns["article_no"])
_LAW_TITLE_EXTRACTOR = PairedSymbolExtractor(("《", "》"), False, "outermost", True)
_ABBR_DEFINITION_EXTRACTOR = PatternExtractor(patterns["abbr_definition"], group=1)
_PAIRED_BRACKETS_EXTRACTOR: Final = PatternExtractor(patterns["paired_brackets"])
_KEYWORD_MAPPING: dict[str, list[str]] = io_util.load_resource_json(
    "KeywordMapping.json"
)


def extract(text: str) -> list[Entity]:
    return _post_process(text, _extract_entities_lazy(text))


def _extract_entities_lazy(text: str) -> Iterator[Entity]:
    """
    Extracts all relevant entities from the input text, including those found via
    bracketed expressions, keyword-based extraction, and direct pattern matching.

    Returns a mapping from EntityType to a list of Entity objects.
    """
    # Extract entities within paired brackets (e.g., Issue No, Law Abbreviation)
    bracket_entities = list(_extract_bracketed_entities(text))
    abbr_defs = [x for x in bracket_entities if x.entity_type == EntityType.LAW_ABBR]

    # Extract entities by keywords, using abbreviations found in brackets as keywords
    keyword_entities = _extract_keyword_entities(text, abbr_defs)

    # Extract entities using direct pattern-based extractors
    pattern_entities = _extract_pattern_entities(text)

    # Merge all entity mappings, giving precedence to earlier updates.
    return chain(bracket_entities, keyword_entities, pattern_entities)


def _extract_pattern_entities(text: str) -> Generator[Entity, Any, None]:
    """
    Extracts entities from the text using predefined pattern-based extractors.
    """
    type_to_extractor: dict[EntityType, Extractor] = {
        EntityType.DATE: _DATE_EXTRACTOR,
        EntityType.CASE_NO: _CASE_NO_EXTRACTOR,
        EntityType.LAW_TITLE: _LAW_TITLE_EXTRACTOR,
        EntityType.LAW_ARTICLE_NO: _ARTICLE_NO_EXTRACTOR,
    }

    for entity_type, extractor in type_to_extractor.items():
        segments = extractor.extract(text)
        yield from (Entity.of(segment, entity_type) for segment in segments)


def _extract_bracketed_entities(text: str) -> Generator[Entity, Any, None]:
    """
    Extracts entities that are defined within paired brackets,
    such as Issue No and Law Abbreviation.
    """
    type_to_extractor = {
        EntityType.ISSUE_NO: _ISSUE_NO_EXTRACTOR,
        EntityType.LAW_ABBR: _ABBR_DEFINITION_EXTRACTOR,
    }

    found_segments = _PAIRED_BRACKETS_EXTRACTOR.extract(text)

    for segment in found_segments:
        offset = segment.start
        inner_text = segment.text

        for entity_type, extractor in type_to_extractor.items():
            for entity in extractor.extract(inner_text):
                yield Entity(
                    text=entity.text,
                    start=entity.start + offset,
                    end=entity.end + offset,
                    entity_type=entity_type,
                )


def _extract_keyword_entities(
    text: str, abbr_entities: list[Entity]
) -> Generator[Entity, Any, None]:
    """
    Extracts entities from the text based on provided keyword mappings.
    The mapping should be from label (str) to a list of keywords (str).
    """
    # Build a reverse mapping from keyword to label
    keyword_to_type = {
        **{k: label for label, kws in _KEYWORD_MAPPING.items() for k in kws},
        **{e.text: EntityType.LAW_ABBR.name for e in abbr_entities},
    }
    abbr_to_entity = {entity.text: entity for entity in abbr_entities}

    extractor = KeywordExtractor(keywords=keyword_to_type.keys(), ignore_overlaps=True)
    found_segments = extractor.extract(text)

    for segment in found_segments:
        type_ = keyword_to_type.get(segment.text)

        if type_ is None:
            raise ValueError(f"Unknown keyword: {segment.text}")

        abbr_def = abbr_to_entity.get(segment.text)
        if abbr_def and segment.start < abbr_def.start:
            logger.debug(f"Ignored 'LAW_ABBR' before its definition:: {segment}")

        entity_type = EntityType.__members__.get(type_.upper())
        if entity_type is None:
            logger.debug(f"Ignored entity with unrecognized type '{type_}': {segment}")
            continue

        yield Entity.of(segment, entity_type)


def _post_process(text: str, entities: Iterable[Entity]) -> list[Entity]:
    # If two entities have the same (start, end), the first one will remain,
    # so the earlier position has higher priority.
    entities = resolve_overlaps(entities, "longest", direct_only=True)

    # Valid entity text is a valid XML fragment without unclosed tags
    predicates: tuple[Callable[[str, Segment], bool]] = (_is_valid_xml_fragment,)

    return [x for x in entities if all(p(text, x) for p in predicates)]


def _is_valid_xml_fragment(document: str, segment: Segment) -> bool:
    """
    Check whether a text segment is a valid XML fragment.
    """
    text = text_util.unescape_html_entities(segment.text)

    # inside attribute value <p attr="xxx text">...</p>
    nearest_start = document.rfind("<", 0, segment.start)
    nearest_end = document.rfind(">", 0, segment.start)
    if nearest_start != -1 and nearest_start < nearest_end:
        return False

    # strict validation
    try:
        ET.fromstring(f"<root>{text}</root>")  # noqa: S314
    except ET.ParseError:
        return False

    return True
