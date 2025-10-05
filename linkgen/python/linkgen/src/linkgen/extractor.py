import logging
import os
from collections.abc import Generator, Iterator
from typing import Any, Final, override

import cn2an  # type: ignore[import-untyped]

from linkgen.config import patterns
from linkgen.helper import (
    Extractor,
    KeywordExtractor,
    PairedSymbolExtractor,
    PatternExtractor,
)
from linkgen.models import Entity, EntityType
from linkgen.utils import coll_util, io_util, text_util

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", logging.DEBUG))


class CaseNoExtractor(Extractor):
    """Extractor for case numbers.

    This extractor identifies single or comma-like separated case numbers and
    yields one entity per case number. It supports inputs such as:

    - "(2025)沪0101刑初第682号"
    - "(2025)沪0101刑初第682号、第683号"
    - "(2025)沪0101刑初第682、683号"
    - "(2025)沪0101刑初682、683号"

    When multiple case numbers are listed with shared non-numeric prefixes
    (e.g., "第" and other fixed parts), the first item is treated as the
    full reference and the subsequent items inherit the same prefix so that
    each yielded entity contains a complete case number string.
    """

    _extractor = PatternExtractor(patterns["case_no"])

    @override
    def extract(self, text: str) -> Iterator[Entity]:
        """Extract case number entities from the given text.

        Args
        - text: The original input text to scan.

        Yields
        - Entity objects of type CASE_NO. For segments containing multiple
          case numbers separated by comma-like delimiters, one entity is
          yielded per case number.
        """
        for segment in self._extractor.extract(text):
            parts = text_util.split_by_equivalents(segment.text, ",")

            if len(parts) == 1:
                yield Entity.of(segment, EntityType.CASE_NO)
            else:
                yield from self._extract_continuous(
                    segment.text,
                    segment.start,
                    parts,
                )

    def _extract_continuous(
        self, _text: str, offset: int, parts: list[str]
    ) -> Generator[Entity, None, None]:
        """Yield case numbers from a segmented list that shares a prefix.

        Args
        - text: The full matched segment text that contains one or more items.
        - offset: The starting index of the matched segment within the source text.
        - parts: Items split by comma-like delimiters, preserving original order.

        Notes
        - Offsets for subsequent items assume a single-character delimiter.
            This mirrors the prior behavior and the expected inputs.
        """
        prefix = None

        for part in parts:
            alias = None
            if prefix is None:
                _, index = text_util.find_last_numeric_suffix(part)
                # If no numeric suffix can be determined, skip.
                if index <= 0:
                    logger.debug("Ignored CASE_NO without valid court id: %r", part)
                    break
                # Derive the shared prefix from the current part
                # to match the index basis
                alias = f"{part.strip().rstrip('号')}号"
                prefix = part[:index]
            else:
                alias = f"{prefix}{part.strip().strip('第号')}号"

            yield Entity(
                text=part,
                start=offset,
                end=offset + len(part),
                entity_type=EntityType.CASE_NO,
                alias=alias,
            )
            offset = offset + len(part) + 1


class LawArticleExtractor(Extractor):
    """Extractor for law article references.

    Supports single and comma-like separated article mentions and yields one
    entity per article. Examples it handles:

    - "第一条"
    - "第一、二条"
    - "第一条、第二条"

    For each part, the numeric portion written in Chinese numerals is
    converted to an integer and exposed via the entity's `alias` field as a
    normalized Arabic number string (e.g., "1", "2").
    """

    _extractor = PatternExtractor(patterns["article_no"])

    @override
    def extract(self, text: str) -> Iterator[Entity]:
        """Extract law article entities from the given text.

        Args
        - text: The input text to scan for article references.

        Yields
        - Entity objects of type LAW_ARTICLE. The `alias` contains the
          normalized article number as an Arabic numeral string.
        """
        for segment in self._extractor.extract(text):
            offset = segment.start
            parts = text_util.split_by_equivalents(segment.text, ",")
            for part in parts:
                art_num = self._to_art_num(part)
                if art_num is None:
                    logger.debug(
                        "Ignored LAW_ARTICLE part without valid numeral: %r", part
                    )
                else:
                    yield Entity(
                        text=part,
                        start=offset,
                        end=offset + len(part),
                        alias=str(art_num),
                        entity_type=EntityType.LAW_ARTICLE,
                    )
                offset = offset + len(part) + 1

    def _to_art_num(self, text: str) -> int | None:
        """Convert a Chinese-numeral article label to an integer.

        Accepts inputs like "第一条", "第二条" or partial parts like "第一" (when
        split by delimiters). Returns None when conversion fails.
        """
        try:
            # remove ' ', '第' and '条'
            cn_num = text.strip().strip("第条")
            if not cn_num:
                return None
            art_num = cn2an.cn2an(cn_num, "normal")
            return int(art_num)
        except Exception:
            return None


class DynamicKeywordEntityExtractor(Extractor):
    """Extract entities based on keyword mappings, including dynamic entries.

    Uses a keyword→type lookup built from a static resource and optionally
    extended by dynamic abbreviation definitions discovered earlier in the
    text. Dynamic entries map the keyword directly to the defining `Entity`.
    """

    _KEYWORD_MAPPING: Final = io_util.load_resource_json("KeywordMapping.json")

    _default_keyword_lookup = {
        k: type_ for type_, kws in _KEYWORD_MAPPING.items() for k in kws
    }
    _default_extractor = KeywordExtractor(
        keywords=_default_keyword_lookup.keys(), ignore_overlaps=True
    )

    def __init__(self, dynamic_abbr_defs: list[Entity]) -> None:
        self._extractor = self._default_extractor
        self._keyword_lookup: dict[str, Any] = self._default_keyword_lookup
        if dynamic_abbr_defs:
            self._rebuild_lookup_and_extractor(dynamic_abbr_defs)

    @override
    def extract(self, text: str) -> Iterator[Entity]:
        """Extract entities by matching keywords and mapping them to types.

        Dynamic abbreviations are validated to ensure their match appears
        after the definition.
        """
        found_segments = self._extractor.extract(text)
        for segment in found_segments:
            value = self._keyword_lookup.get(segment.text)

            if value is None:
                logger.debug("Ignored keyword with no mapping: %r", segment)
                continue

            # dynamic abbreviation
            entity_type = None
            abbr_def = None
            if isinstance(value, Entity):
                if segment.start < value.start:
                    logger.debug("Ignored LAW_ABBR before its definition: %r", segment)
                    continue
                abbr_def = value
                entity_type = value.entity_type
            else:
                entity_type = EntityType.__members__.get(value.upper())
                if entity_type is None:
                    logger.debug(
                        "Ignored unrecognized entity type %r for %r", value, segment
                    )
                    continue

            yield Entity.of(segment, entity_type, refers_to=abbr_def)

    def _rebuild_lookup_and_extractor(self, dynamic_abbr_defs: list[Entity]) -> None:
        # Build a reverse mapping from keyword to label/entity
        self._keyword_lookup = {
            **self._default_keyword_lookup,
            **{e.text: e for e in dynamic_abbr_defs},
        }
        self._extractor = KeywordExtractor(
            keywords=self._keyword_lookup.keys(), ignore_overlaps=True
        )


class PatternEntityExtractor(Extractor):
    """Extract entities via simple, stateless pattern extractors.

    Currently extracts:
    - `EntityType.DATE` via a regex pattern
    - `EntityType.LAW_TITLE` via paired symbols "《...》" (outermost)
    """

    _extractor_by_type: dict[EntityType, Extractor] = {
        EntityType.DATE: PatternExtractor(patterns["date"]),
        EntityType.LAW_TITLE: PairedSymbolExtractor(
            symbol_pair=("《", "》"),
            include_symbols=False,
            strategy="outermost",
            allow_fallback_on_unclosed=True,
        ),
    }

    @override
    def extract(self, text: str) -> Iterator[Entity]:
        """Run all configured pattern extractors over the text.

        Yields
        - Entities converted from matched segments, with their corresponding
          `EntityType`.
        """
        for entity_type, extractor in self._extractor_by_type.items():
            yield from (
                Entity.of(segment, entity_type) for segment in extractor.extract(text)
            )


class BracketEntityExtractor(Extractor):
    """Extract entities appearing inside paired brackets.

    Handles content within bracketed segments and applies specialized
    extractors to the inner text for:
    - `EntityType.ISSUE_NO`
    - `EntityType.LAW_DYNAMIC_ABBR`
    """

    _extractor_by_type: dict[EntityType, Extractor] = {
        EntityType.ISSUE_NO: PatternExtractor(
            patterns["issue_nos"], stop_on_first=True, group=1
        ),
        EntityType.LAW_DYNAMIC_ABBR: PatternExtractor(
            patterns["abbr_definition"], group=1
        ),
    }
    _brackets_extractor = PatternExtractor(patterns["paired_brackets"])

    @override
    def extract(self, text: str) -> Iterator[Entity]:
        """Extract entities from inner content of bracketed segments."""
        found_segments = self._brackets_extractor.extract(text)
        for segment in found_segments:
            offset = segment.start
            inner_text = segment.text

            for entity_type, extractor in self._extractor_by_type.items():
                for entity in extractor.extract(inner_text):
                    yield Entity(
                        text=entity.text,
                        start=entity.start + offset,
                        end=entity.end + offset,
                        entity_type=entity_type,
                    )


# Global extractors
_CASE_NO_EXTRACTOR: Final = CaseNoExtractor()
_ARTICLE_EXTRACTOR: Final = LawArticleExtractor()
_PATTERN_ENTITY_EXTRACTOR: Final = PatternEntityExtractor()
_BRACKET_ENTITY_EXTRACTOR: Final = BracketEntityExtractor()


def extract_entities(text: str) -> Iterator[Entity]:
    """Yield all entities found in the text.

    Extraction order:
    1) Bracketed entities (captured for dynamic keywords, yielded last)
    2) Case numbers
    3) Law articles
    4) Simple pattern entities (dates, law titles)
    5) Keyword-based entities (promulgator, law_abbr, including dynamic abbreviations)
    6) Bracketed entities (yielded at the end)
    """

    # Extract entities within paired brackets (e.g., Issue No, Law Abbreviation)
    bracket_entities = list(_BRACKET_ENTITY_EXTRACTOR.extract(text))
    dynamic_abbr_defs = coll_util.remove_if(
        bracket_entities, key=lambda x: x.entity_type == EntityType.LAW_DYNAMIC_ABBR
    )

    extractors = (
        _CASE_NO_EXTRACTOR,
        _ARTICLE_EXTRACTOR,
        _PATTERN_ENTITY_EXTRACTOR,
        # Extract keyword-based entities using abbreviations found in brackets
        DynamicKeywordEntityExtractor(dynamic_abbr_defs),
    )

    # yield all entities, with earlier ones taking precedence.
    for extractor in extractors:
        yield from extractor.extract(text)

    yield from bracket_entities
