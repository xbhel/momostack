# -*- coding: utf-8 -*
# -*- python: 3.12 -*

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import orjson


@dataclass
class Property[T]:
    type: str
    value: T
    description: str
    required: bool = True
    constraints: List[str] = field(default_factory=list)


class PropProvider(ABC):
    @abstractmethod
    def is_support(self, property: Property) -> bool:
        pass

    @abstractmethod
    def provide(self, property: Property) -> Property:
        pass

class ObjectProperty(Property):
    properties: List[Property]


def parse_schema(schema_json: str) -> dict:
    return orjson.loads(schema_json)


