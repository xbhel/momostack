from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto, unique
from typing import Self


@unique
class EntityType(StrEnum):
    depends_on: tuple[Self, ...]

    DATE = auto(), ()
    ISSUE_NO = auto(), ()
    PROMULGATOR = auto(), ()
    CASE_NO = auto(), ()
    LAW_TITLE = auto(), (DATE, ISSUE_NO, PROMULGATOR)
    LAW_SELF = auto(), (LAW_TITLE,)
    LAW_ARTICLE_NO = auto(), (LAW_TITLE,)
    LAW_ABBR = auto(), (LAW_TITLE,)

    def __new__(
        cls,
        value: str,
        depends_on: tuple[Self, ...],
    ) -> EntityType:
        obj = str.__new__(cls, value)
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
    attrs: list[Entity] | None = None
    refers_to: Entity | None = None

    @classmethod
    def of(
        cls,
        segment: Segment,
        entity_type: EntityType,
        attrs: list[Entity] | None = None,
        refers_to: Entity | None = None,
    ) -> Self:
        return cls(
            text=segment.text,
            start=segment.start,
            end=segment.end,
            entity_type=entity_type,
            attrs=attrs,
            refers_to=refers_to,
        )

    def add_attr(self, attr: Entity) -> None:
        if self.attrs is None:
            self.attrs = []
        self.attrs.append(attr)
