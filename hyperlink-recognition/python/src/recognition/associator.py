from collections import defaultdict
from collections.abc import Iterable

from recognition.datamodels import Entity, EntityType


def associate(entities: Iterable[Entity]) -> Iterable[Entity]:
    type_to_entities = _group_by_type(entities)
    print(type_to_entities)
    return entities


def _group_by_type(entities: Iterable[Entity]) -> dict[EntityType, list[Entity]]:
    type_to_entities: dict[EntityType, list[Entity]] = defaultdict(list)
    for entity in entities:
        type_to_entities[entity.entity_type].append(entity)
    return type_to_entities
