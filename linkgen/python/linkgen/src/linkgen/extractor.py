import logging
import os
from collections.abc import Generator, Iterator
from itertools import chain
from typing import Any, Final

from linkgen.config import patterns
from linkgen.helper import (
    Extractor,
    KeywordExtractor,
    PairedSymbolExtractor,
    PatternExtractor,
)
from linkgen.models import Entity, EntityType
from linkgen.utils import io_util

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))

# Global extractors
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


def extract_entities(text: str) -> Iterator[Entity]:
    """
    Extracts all relevant entities from the input text, including those found via
    bracketed expressions, keyword-based extraction, and direct pattern matching.

    Returns a mapping from EntityType to a list of Entity objects.
    """
    # Extract entities within paired brackets (e.g., Issue No, Law Abbreviation)
    bracket_entities = list(_extract_bracketed_entities(text))
    dynamic_abbr_defs = [
        x for x in bracket_entities if x.entity_type == EntityType.LAW_DYNAMIC_ABBR
    ]

    # Extract entities by keywords, using abbreviations found in brackets as keywords
    keyword_entities = _extract_keyword_entities(text, dynamic_abbr_defs)

    # Extract entities using direct pattern-based extractors
    pattern_entities = _extract_pattern_entities(text)

    # Merge all entity mappings, giving precedence to earlier updates.
    return chain(bracket_entities, keyword_entities, pattern_entities)


def _extract_pattern_entities(text: str) -> Generator[Entity, Any, None]:
    """
    Extracts entities from the text using predefined pattern-based extractors.
    """
    extractor_by_type: dict[EntityType, Extractor] = {
        EntityType.DATE: _DATE_EXTRACTOR,
        EntityType.CASE_NO: _CASE_NO_EXTRACTOR,
        EntityType.LAW_TITLE: _LAW_TITLE_EXTRACTOR,
        EntityType.LAW_ARTICLE_NO: _ARTICLE_NO_EXTRACTOR,
    }

    for entity_type, extractor in extractor_by_type.items():
        segments = extractor.extract(text)
        yield from (Entity.of(segment, entity_type) for segment in segments)


def _extract_bracketed_entities(text: str) -> Generator[Entity, Any, None]:
    """
    Extracts entities that are defined within paired brackets,
    such as Issue No and Law Abbreviation.
    """
    extractor_by_type: dict[EntityType, Extractor] = {
        EntityType.ISSUE_NO: _ISSUE_NO_EXTRACTOR,
        EntityType.LAW_DYNAMIC_ABBR: _ABBR_DEFINITION_EXTRACTOR,
    }

    found_segments = _PAIRED_BRACKETS_EXTRACTOR.extract(text)

    for segment in found_segments:
        offset = segment.start
        inner_text = segment.text

        for entity_type, extractor in extractor_by_type.items():
            for entity in extractor.extract(inner_text):
                yield Entity(
                    text=entity.text,
                    start=entity.start + offset,
                    end=entity.end + offset,
                    entity_type=entity_type,
                )


def _extract_keyword_entities(
    text: str, dynamic_abbr_defs: list[Entity]
) -> Generator[Entity, Any, None]:
    """
    Extracts entities from the text based on provided keyword mappings.
    The mapping should be from label (str) to a list of keywords (str).
    """
    # Build a reverse mapping from keyword to label
    keyword_to_type = {
        **{k: label for label, kws in _KEYWORD_MAPPING.items() for k in kws},
        **{e.text: e.entity_type.name for e in dynamic_abbr_defs},
    }
    abbr_def_to_entity = {entity.text: entity for entity in dynamic_abbr_defs}

    extractor = KeywordExtractor(keywords=keyword_to_type.keys(), ignore_overlaps=True)
    found_segments = extractor.extract(text)

    for segment in found_segments:
        type_ = keyword_to_type.get(segment.text)

        if type_ is None:
            raise ValueError(f"Unknown keyword: {segment.text}")

        entity_type = EntityType.__members__.get(type_.upper())
        if entity_type is None:
            logger.debug(f"Ignored entity with unrecognized type '{type_}': {segment}")
            continue

        # dynamic abbreviation
        abbr_def = abbr_def_to_entity.get(segment.text)
        if abbr_def and segment.start < abbr_def.start:
            logger.debug(f"Ignored '{segment}' before its definition: {abbr_def}")
            continue

        yield Entity.of(segment, entity_type, refers_to=abbr_def)
