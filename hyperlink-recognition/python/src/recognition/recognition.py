from recognition.datamodels import Entity
from recognition.extractor import extract_entities
from recognition.resolver import resolve_entities


def recognize(text: str) -> list[Entity]:
    entities = extract_entities(text)
    return resolve_entities(text, entities)
