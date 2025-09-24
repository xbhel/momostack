from collections.abc import Iterable

from recognition.datamodels import Entity
from structures import LookupDict
from utils import coll_util


def associate(entities: Iterable[Entity]) -> Iterable[Entity]:
    entities_by_type = coll_util.group_by(entities, key=lambda x: x.entity_type)
    # associate_by_nearest_backward
    # associate_by_nearest_forward
    print(entities_by_type)
    return entities


def associate_attribute_date(entities: list[Entity], attrs: list[Entity]) -> None:
    end_index_lookup = LookupDict({x.end: x for x in attrs})
    start_index_lookup = LookupDict({x.start: x for x in attrs})

    for entity in entities:
        if attr := end_index_lookup.ceiling(entity.end):
            entity.add_attr(attr)
        if attr := start_index_lookup.floor(entity.start):
            entity.add_attr(attr)
