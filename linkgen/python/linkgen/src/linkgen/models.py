from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto, unique
from typing import Self

__author__ = "xbhel"
__email__ = "xbhel@outlook.com"


@unique
class EntityType(StrEnum):
    _depends_on_name_: tuple[str, ...]

    DATE = auto(), ()
    ISSUE_NO = auto(), ()
    PROMULGATOR = auto(), ()
    CASE_NO = auto(), ()
    LAW_ABBR = auto(), ()
    THIS_LAW = auto(), ("LAW_TITLE",)
    LAW_SELF = auto(), ("LAW_TITLE",)
    LAW_DYNAMIC_ABBR = auto(), ("LAW_TITLE",)
    LAW_TITLE = auto(), ("DATE", "ISSUE_NO", "PROMULGATOR")
    LAW_ARTICLE = (
        auto(),
        ("LAW_TITLE", "LAW_DYNAMIC_ABBR", "LAW_ABBR", "THIS_LAW", "LAW_SELF"),
    )

    def __new__(
        cls,
        value: str,
        depends_on_name: tuple[str, ...],
    ) -> EntityType:
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._depends_on_name_ = depends_on_name
        return obj

    @property
    def depends_on(self) -> tuple[EntityType, ...]:
        return tuple(EntityType[x] for x in self._depends_on_name_)


@dataclass
class Token:
    text: str
    start: int  # inclusive
    end: int  # exclusive

    def overlaps_with(self, other: Self) -> bool:
        return self.start < other.end and self.end > other.start

    def contains(self, other: Self) -> bool:
        return self.start <= other.start and self.end >= other.end


@dataclass
class Entity(Token):
    entity_type: EntityType
    attrs: list[Entity] = field(default_factory=list)
    refers_to: Entity | None = None
    alias: str | None = None

    @classmethod
    def of(
        cls,
        segment: Token,
        entity_type: EntityType,
        attrs: list[Entity] | None = None,
        refers_to: Entity | None = None,
        alias: str | None = None
    ) -> Self:
        if attrs is None:
            attrs = []
        return cls(
            text=segment.text,
            start=segment.start,
            end=segment.end,
            entity_type=entity_type,
            attrs=attrs,
            refers_to=refers_to,
            alias=alias
        )


@dataclass
class TokenSpan:
    core: Token
    normalized_text: str
    nested: bool = False
    nested_normalized_text: str | None = None
    prefixes: list[Token] = field(default_factory=list)
    suffixes: list[Token] = field(default_factory=list)

    @property
    def text_prefixes(self) -> list[str]:
        return [x.text for x in self.prefixes]

    @property
    def text_suffixes(self) -> list[str]:
        return [x.text for x in self.suffixes]

    @property
    def core_term(self) -> str:
        return self.core.text


@dataclass
class DocMeta:
    doc_id: str
    doc_type: str
    doc_url: str
    title: str
    core_term: str
    status: str
    created_at: int
    updated_at: int
    release_date: str
    effective_status: str
    effective_date: str
    effective_scope: str
    issue_no: str
    timestamp_version: int
    promulgators: list[str]
