from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal


@dataclass
class Entity:
    text: str
    start: int
    end: int
    category: str
    type: str
    attrs: list[str] | None = None


class Extractor(ABC):
    @abstractmethod
    def extract(self, paragraph: str) -> Iterable[Entity]:
        raise NotImplementedError


NestingStrategy = Literal["outermost", "innermost", "all"]


class SymbolBasedExtractor(Extractor):
    def __init__(self, strategy: NestingStrategy = "all"):
        """
        :param strategy: defines how to handle nested paired symbols
                         "outermost": keep only the widest enclosing pair
                         "innermost": keep only the deepest enclosed pair
                         "all": keep all matched pairs (default)
        """
        self.strategy = strategy

    def extract(self, paragraph: str) -> Iterable[Entity]:
        """
        Extract text enclosed in paired symbols (e.g., 《...》) as entities.
        Handles nested symbols based on the configured strategy.
        """
        return []
