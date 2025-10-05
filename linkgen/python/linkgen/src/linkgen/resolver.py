import xml.etree.ElementTree as ET
from collections.abc import Callable, Generator, Iterable, Iterator
from itertools import chain
from typing import Any, Final

from linkgen.helper import resolve_overlaps
from linkgen.models import Entity, EntityType
from linkgen.structures import LookupDict
from linkgen.utils import coll_util, text_util

_LEFT_BRACKETS: Final = {"(", "（"}  # noqa: RUF001
_SENTENCE_ENDING: Final = {"?", "!", ".", "。", "？", "！"}  # noqa: RUF001


def resolve_entities(text: str, entities_it: Iterator[Entity]) -> list[Entity]:
    # Post-process to filter out invalid entities
    entities_it = _validate_entities(text, entities_it)

    # If two entities have the same (start, end), the first one will remain,
    # so the earlier position has higher priority.
    entity_list = resolve_overlaps(entities_it, strategy="longest", direct_only=True)

    _associate_entities(text, entity_list)
    return _remove_orphan_entities(entity_list)


def _validate_entities(
    text: str, entities: Iterable[Entity]
) -> Generator[Entity, Any, None]:
    """
    Valid entity text is a valid XML fragment without unclosed tags
    """
    validations: tuple[Callable[[str, Entity], bool], ...] = (
        _is_unmarked_hyperlink,
        _is_valid_xml_fragment,
    )
    yield from (x for x in entities if all(v(text, x) for v in validations))


def _associate_entities(text: str, entities: list[Entity]) -> None:
    """
    Associate entities with their attributes based on entity type dependencies.
    """
    if not entities:
        return

    associators = {
        EntityType.LAW_TITLE: _associate_attributes,
        EntityType.LAW_SELF: _associate_ref_definitions,
        EntityType.THIS_LAW: _associate_ref_definitions,
        EntityType.LAW_ARTICLE: _associate_ref_definitions,
        EntityType.LAW_DYNAMIC_ABBR: _associate_ref_defs_for_dynamic_abbr,
    }

    entities_by_type = coll_util.group_by(entities, key=lambda x: x.entity_type)

    for entity_type, group in entities_by_type.items():
        if entity_type.depends_on and (func := associators.get(entity_type)):
            depends_on = chain.from_iterable(
                entities_by_type.get(x, []) for x in entity_type.depends_on
            )
            func(text, group, depends_on)


def _remove_orphan_entities(entities: Iterable[Entity]) -> list[Entity]:
    """
    Remove entities that require a reference but have none.
    LAW_TITLE, CASE_NO and LAW_ABBR are allowed to exist independently.
    """
    remaining_types = {
        EntityType.CASE_NO,
        EntityType.LAW_ABBR,
        EntityType.LAW_SELF,
        EntityType.LAW_TITLE,
    }
    return [x for x in entities if x.refers_to or x.entity_type in remaining_types]


def _associate_ref_definitions(
    text: str,
    entities: list[Entity],
    references: Iterator[Entity],
) -> None:
    """
    Link entities to the nearest reference before them.
    """
    end_index_lookup = LookupDict({x.end: x for x in references})

    for entity in entities:
        # forward lookup
        if (
            ref := end_index_lookup.floor(entity.start - 1)
        ) and _without_sentence_ending(text, ref.end, entity.start):
            entity.refers_to = ref


def _associate_ref_defs_for_dynamic_abbr(
    text: str,
    entities: list[Entity],
    references: Iterator[Entity],
) -> None:
    """
    Link entities to the nearest reference before them for dynamic abbreviations.
    """
    end_index_lookup = LookupDict({x.end: x for x in references})

    for abbr_ref in entities:
        if abbr_ref.refers_to is None:
            raise ValueError(f"Missing definition for dynamic abbreviation {abbr_ref}")

        abbr_def = abbr_ref.refers_to
        # forward lookup
        if (ref := end_index_lookup.floor(abbr_def.start - 1)) and (
            _without_sentence_ending(text, ref.end, abbr_def.start)
            and _startswith_single_left_bracket(text, ref.end, abbr_def.start)
        ):
            abbr_ref.refers_to = ref
        else:
            abbr_ref.refers_to = None


def _associate_attributes(
    text: str, entities: list[Entity], attrs: Iterator[Entity]
) -> None:
    """
    Associate attributes (dates, issue numbers, promulgators) with entities.
    """
    forward_lookup_types = (EntityType.ISSUE_NO, EntityType.DATE)
    end_index_lookup = LookupDict({x.end: x for x in entities})
    start_index_lookup = LookupDict({x.start: x for x in entities})

    for attr in attrs:
        # forward lookup
        if attr.entity_type in forward_lookup_types:
            entity = end_index_lookup.floor(attr.start - 1)
            if (
                entity
                and _without_sentence_ending(text, entity.end, attr.start)
                and _startswith_single_left_bracket(text, entity.end, attr.start)
            ):
                entity.attrs.append(attr)
                # A attribute by forward lookup can only be occupied by an entity.
                continue

        # backward lookup
        entity = start_index_lookup.ceiling(attr.end)
        if entity and _without_sentence_ending(text, attr.end, entity.start):
            entity.attrs.append(attr)


def _is_valid_xml_fragment(document: str, segment: Entity) -> bool:
    """
    Check whether a text segment is a valid XML fragment.
    """
    text = text_util.unescape_html_entities(segment.text)

    # inside attribute value(e.g., <tag attr="...">)
    last_open = document.rfind("<", 0, segment.start)
    last_close = document.rfind(">", 0, segment.start)
    if last_open != -1 and last_close < last_open:
        return False

    # strict validation
    try:
        ET.fromstring(f"<root>{text}</root>")  # noqa: S314
    except ET.ParseError:
        return False

    return True


def _is_unmarked_hyperlink(document: str, segment: Entity) -> bool:
    """
    Check whether a text segment is already marked with an <a> tag.
    """
    last_open = document.rfind("<a", 0, segment.start)
    if last_open == -1:
        return True
    last_close = document.rfind("</a>", 0, segment.start)
    return last_close != -1 and last_close > last_open


def _without_sentence_ending(text: str, start: int, end: int) -> bool:
    """
    Check if the given range does not contain any sentence-ending character.
    """
    return all(text.find(x, start, end) == -1 for x in _SENTENCE_ENDING)


def _startswith_single_left_bracket(text: str, start: int, end: int) -> bool:
    """
    Check if the text range starts with exactly one left bracket.

    This function skips whitespace and HTML/XML tags, then verifies that:
    1. The first non-whitespace character is a left bracket
    2. There are no other left brackets in the range
    """
    # Skip leading whitespace and HTML/XML tags
    idx = _skip_whitespace_and_tags(text, start, end)

    # Ensure the first non-space character is a left bracket
    if idx >= end or text[idx] not in _LEFT_BRACKETS:
        return False

    # Check if there is another left bracket in range
    return not any(text.find(x, idx + 1, end) != -1 for x in _LEFT_BRACKETS)


def _skip_whitespace_and_tags(text: str, start: int, end: int) -> int:
    """
    Skip leading whitespace and HTML/XML tags in the given range.
    """
    idx = start
    while idx < end:
        # Skip whitespace
        next_idx = _skip_leading_whitespace(text, idx, end)
        # Skip HTML/XML tags
        next_idx = _skip_leading_element_tag(text, next_idx, end)
        if next_idx == idx:
            break

        idx = next_idx

    return idx


def _skip_leading_whitespace(text: str, start: int, end: int) -> int:
    """
    Move past leading whitespace characters.
    """
    while start < end and text_util.is_whitespace(text[start]):
        start += 1
    return start


def _skip_leading_element_tag(text: str, start: int, end: int) -> int:
    """
    Move past leading HTML/XML element tags.
    """
    if text[start] == "<":
        nearest_close = text.find(">", start, end)
        if nearest_close > start:
            return nearest_close + 1
    return start
