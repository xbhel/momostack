from dataclasses import dataclass
from enum import Enum, unique
from typing import Self


@unique
class EntityType(int, Enum):
    DATE = (1,)
    ISSUE_NO = (2,)
    PROMULGATOR = (3,)
    CASE_NO = (4,)
    LAW_TITLE = 5, (DATE, ISSUE_NO, PROMULGATOR)
    LAW_ARTICLE_NO = 6, (LAW_TITLE,)
    LAW_ABBR = 7, (LAW_TITLE,)
    LAW_SELF = 8, (LAW_TITLE,)

    def __init__(
        self,
        code: int,
        depends_on: tuple[Self, ...],
    ) -> None:
        self.code = code
        self.depends_on = depends_on


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
    # category: str
    entity_type: EntityType
    attrs: list[str] | None = None

    @classmethod
    def of(
        cls,
        segment: Segment,
        entity_type: EntityType,
        attrs: list[str] | None = None,
    ) -> Self:
        return cls(
            text=segment.text,
            start=segment.start,
            end=segment.end,
            entity_type=entity_type,
            attrs=attrs,
        )
