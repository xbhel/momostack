from dataclasses import dataclass
from enum import Enum, unique
from typing import Self


@unique
class EntityType(int, Enum):
    depends_on: tuple[Self, ...]

    DATE = 1, ()
    ISSUE_NO = 2, ()
    PROMULGATOR = 3, ()
    CASE_NO = 4, ()
    LAW_SELF = 5, ()
    LAW_TITLE = 6, (DATE, ISSUE_NO, PROMULGATOR)
    LAW_ARTICLE_NO = 7, (LAW_TITLE,)
    LAW_ABBR = 8, (LAW_TITLE,)

    def __new__(
        cls,
        value: int,
        depends_on: tuple[Self, ...],
    ) -> "EntityType":
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.depends_on = depends_on or ()
        return obj


@dataclass
class Segment:
    text: str
    start: int  # inclusive
    end: int  # exclusive

    def overlaps_with(self, other: Self) -> bool:
        return self.start < other.end and self.end > other.start

    def contains(self, other: Self) -> bool:
        return self.start <= other.start and self.end >= other.end


@dataclass
class Entity(Segment):
    # category: str
    entity_type: EntityType
    attrs: list["Entity"] | None = None

    @classmethod
    def of(
        cls,
        segment: Segment,
        entity_type: EntityType,
        attrs: list["Entity"] | None = None,
    ) -> Self:
        return cls(
            text=segment.text,
            start=segment.start,
            end=segment.end,
            entity_type=entity_type,
            attrs=attrs,
        )

    def add_attr(self, attr: "Entity") -> None:
        if self.attrs is None:
            self.attrs = []
        self.attrs.append(attr)
