from dataclasses import dataclass
from typing import Self


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
    entity_type: str
    attrs: list[str] | None = None


