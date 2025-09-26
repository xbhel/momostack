from collections.abc import Iterable, Iterator
from itertools import chain
from typing import Final

from datamodels import Entity, EntityType

from structures import LookupDict
from utils import coll_util

_LEFT_BRACKETS: Final = {"(", "（"}  # noqa: RUF001
_SENTENCE_ENDING: Final = {"?", "!", "。", "？", "！"}  # noqa: RUF001


def associate(text: str, entities: Iterable[Entity]) -> Iterable[Entity]:
    """
    Associate entities with their attributes based on entity type dependencies.
    """
    associators = {
        EntityType.LAW_TITLE: associate_law_title,
    }
    entities_by_type = coll_util.group_by(entities, key=lambda x: x.entity_type)
    for entity_type, group in entities_by_type.items():
        if entity_type.depends_on and (func := associators.get(entity_type)):
            depends_on = chain.from_iterable(
                entities_by_type.get(x, []) for x in entity_type.depends_on
            )
            func(text, group, depends_on)

    return entities


def associate_law_title(
    text: str, law_titles: list[Entity], attrs: Iterator[Entity]
) -> None:
    """
    Associate attributes (dates, issue numbers, promulgators) with law titles.
    """
    end_index_lookup = LookupDict({x.end: x for x in law_titles})
    start_index_lookup = LookupDict({x.start: x for x in law_titles})

    forward_lookup_types = (EntityType.ISSUE_NO, EntityType.DATE)

    for attr in attrs:
        # forward lookup
        if attr.entity_type in forward_lookup_types:
            entity = end_index_lookup.floor(attr.start - 1)
            if (
                entity
                and _without_sentence_ending(text, entity.end, attr.start)
                and _startswith_single_left_bracket(text, entity.end, attr.start)
            ):
                entity.add_attr(attr)
                # forward attr only be occupy by a entity
                continue

        # backward lookup
        entity = start_index_lookup.ceiling(attr.end)
        if entity and _without_sentence_ending(text, attr.end, entity.start):
            entity.add_attr(attr)


def _without_sentence_ending(text: str, start: int, end: int) -> bool:
    """Check if the given range does not contain any sentence-ending character."""
    return all(text.find(x, start, end) == -1 for x in _SENTENCE_ENDING)


def _startswith_single_left_bracket(text: str, start: int, end: int) -> bool:
    """
    Check if the text range starts with exactly one left bracket.

    This function skips whitespace and HTML/XML tags, then verifies that:
    1. The first non-whitespace character is a left bracket
    2. There are no other left brackets in the range

    Returns:
        True if the range starts with exactly one left bracket
    """
    # Skip leading whitespace and HTML/XML tags
    idx = start
    while True:
        next_idx = _move_space_after(text, idx, end)
        next_idx = _move_element_tag_after(text, next_idx, end)
        if next_idx == idx:
            break
        idx = next_idx

    # Ensure the first non-space character is a left bracket
    if idx >= end or text[idx] not in _LEFT_BRACKETS:
        return False

    # Check if there is another left bracket in range
    return not any(text.find(x, idx + 1, end) != -1 for x in _LEFT_BRACKETS)


def _move_space_after(text: str, start: int, end: int) -> int:
    """Move past leading whitespace characters."""
    return next((i for i in range(start, end) if not text[i].isspace()), end)


def _move_element_tag_after(text: str, start: int, end: int) -> int:
    """Move past leading HTML/XML element tags."""
    if text[start] == "<":
        last_close = text.find(">", start, end)
        if last_close > start:
            return last_close + 1
    return start
