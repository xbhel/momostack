from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import OrderedDict
from collections.abc import ItemsView, Iterator, KeysView, Mapping, ValuesView
from typing import overload

from typings import KT, VT, SupportsRichComparisonT, T


class ReadonlyDict(Mapping[KT, VT]):
    """
    An immutable dictionary-like mapping that prevents modification after creation.

    This class provides a read-only view of a dictionary, raising TypeError
    for any attempt to modify the mapping (assignment, deletion, etc.).

    Example::

        data = {"a": 1, "b": 2}
        readonly = ReadonlyDict(data)
        readonly["a"]  # 1
        readonly["c"] = 3
            # TypeError: 'ReadonlyDict' object does not support item assignment
    """

    __slots__ = "_data"

    def __init__(self, data: dict[KT, VT] | Mapping[KT, VT]) -> None:
        """Initialize with a dictionary or mapping."""
        self._data = dict(data)

    def __getitem__(self, key: KT) -> VT:
        return self._data[key]

    def __iter__(self) -> Iterator[KT]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __setitem__(self, key: KT, value: VT) -> None:
        raise TypeError(
            f"{self.__class__.__name__!r} object does not support item assignment"
        )

    def __delitem__(self, key: KT) -> None:
        raise TypeError(
            f"{self.__class__.__name__!r} object does not support item deletion"
        )

    @overload
    def get(self, key: KT) -> VT | None: ...

    @overload
    def get(self, key: KT, default: T) -> VT | T: ...

    def get(self, key: KT, default: VT | T | None = None) -> VT | T | None:
        """Return the value for key if key is in the dictionary, else default."""
        return self._data.get(key, default)

    def keys(self) -> KeysView[KT]:
        """Return a view of the keys."""
        return self._data.keys()

    def values(self) -> ValuesView[VT]:
        """Return a view of the values."""
        return self._data.values()

    def items(self) -> ItemsView[KT, VT]:
        """Return a view of (key, value) pairs."""
        return self._data.items()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._data!r})"

    def copy(self) -> ReadonlyDict[KT, VT]:
        """Return a shallow copy of the ReadonlyDict."""
        return ReadonlyDict(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ReadonlyDict):
            return self._data == other._data
        if isinstance(other, Mapping):
            return self._data == dict(other)
        return NotImplemented


class LookupDict(ReadonlyDict[SupportsRichComparisonT, VT]):
    """
    An immutable mapping that supports efficient floor/ceiling/lower/higher key lookups.

    Keys must be comparable (support <, >, <=, >=) and hashable. The mapping is
    automatically sorted by key for efficient binary search operations.

    Example::

        data = {3: "three", 1: "one", 4: "four", 2: "two"}
        lookup = LookupDict(data)
        lookup.floor(3)  # "three" (greatest key <= 3)
        lookup.ceiling(2.5)  # "three" (smallest key >= 2.5)
        lookup.lower(3)  # "two" (greatest key < 3)
        lookup.higher(2)  # "three" (smallest key > 2)
    """

    __slots__ = ("_data", "_keys")

    def __init__(
        self,
        data: dict[SupportsRichComparisonT, VT] | Mapping[SupportsRichComparisonT, VT],
    ) -> None:
        ordered = OrderedDict(sorted(data.items(), key=lambda x: x[0]))
        super().__init__(ordered)
        self._keys = list(ordered.keys())

    def floor(self, key: SupportsRichComparisonT) -> VT | None:
        """
        Returns the value associated with the greatest key <= the given key,
        or None if there is no such key.
        """
        pos = bisect_right(self._keys, key)
        if pos == 0:
            return None
        return self._data[self._keys[pos - 1]]

    def ceiling(self, key: SupportsRichComparisonT) -> VT | None:
        """
        Returns the value associated with the smallest key >= the given key,
        or None if there is no such key.
        """
        pos = bisect_left(self._keys, key)
        if pos == len(self._keys):
            return None
        return self._data[self._keys[pos]]

    def lower(self, key: SupportsRichComparisonT) -> VT | None:
        """
        Returns the value associated with the greatest key < the given key,
        or None if there is no such key.
        """
        pos = bisect_left(self._keys, key)
        if pos == 0:
            return None
        return self._data[self._keys[pos - 1]]

    def higher(self, key: SupportsRichComparisonT) -> VT | None:
        """
        Returns the value associated with the smallest key > the given key,
        or None if there is no such key.
        """
        pos = bisect_right(self._keys, key)
        if pos == len(self._keys):
            return None
        return self._data[self._keys[pos]]

    def range(
        self, start: SupportsRichComparisonT | None = None, end: KT | None = None
    ) -> Iterator[tuple[SupportsRichComparisonT, VT]]:
        """
        Return an iterator over (key, value) pairs in the range [start, end).

        Example:
            >>> lookup = LookupDict({1: "a", 3: "c", 5: "e", 7: "g"})
            >>> list(lookup.range(2, 6))  # [(3, "c"), (5, "e")]
        """
        start_pos = 0 if start is None else bisect_left(self._keys, start)
        end_pos = len(self._keys) if end is None else bisect_left(self._keys, end)

        for i in range(start_pos, end_pos):
            key = self._keys[i]
            yield key, self._data[key]
