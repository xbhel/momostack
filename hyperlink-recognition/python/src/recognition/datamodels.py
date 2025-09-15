from dataclasses import dataclass
from enum import Enum, unique
from typing import Self


@unique
class EntityType(str, Enum):
    LAW_TITLE = 1
    LAW_ARTICLE_NO = 2
    LAW_ABBR = 4
    LAW_SELF = 5
    CASE_NO = 3
    DATE = 6
    ISSUE_NO = 7
    PROMULGATOR = 8


@dataclass
class Segment:
    text: str
    start: int  # inclusive
    end: int  # exclusive

    def overlaps_with(self, other: Self) -> bool:
        return self.start < other.end & self.end > other.start

    def contains(self, other: Self) -> bool:
        return self.start <= other.start and self.end >= other.end


@dataclass
class Entity(Segment):
    category: str
    entity_type: EntityType
    attrs: list[str] | None = None
