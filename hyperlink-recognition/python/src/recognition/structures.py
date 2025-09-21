from bisect import bisect_left, bisect_right
from collections import OrderedDict
from collections.abc import ItemsView, Iterator, KeysView, Mapping, ValuesView
from typing import Any, Generic, Protocol, TypeVar


class Comparable(Protocol):
    def __lt__(self, other: Any) -> bool: ...


_VT = TypeVar("_VT")
_KT = TypeVar("_KT", bound=Comparable)


class LookupDict(Mapping[_KT, _VT], Generic[_KT, _VT]):
    """
    An immutable mapping that supports efficient floor/ceiling/lower/higher key lookups.
    Keys must be comparable and hashable.
    """

    __slots__ = ("_data", "_keys")

    def __init__(self, data: dict[_KT, _VT]) -> None:
        self._data = OrderedDict(sorted(data.items(), key=lambda x: x[0]))
        self._keys = list(self._data.keys())

    def __getitem__(self, key: _KT) -> _VT:
        return self._data[key]

    def __iter__(self) -> Iterator[_KT]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __setitem__(self, key: _KT, value: _VT) -> None:
        raise TypeError(
            f"{self.__class__.__name__!r} object does not support item assignment"
        )

    def __delitem__(self, key: _KT) -> None:
        raise TypeError(
            f"{self.__class__.__name__!r} object does not support item deletion"
        )

    def floor(self, key: _KT) -> _VT | None:
        """
        Returns the value associated with the greatest key <= the given key,
        or None if there is no such key.
        """
        pos = bisect_right(self._keys, key)
        if pos == 0:
            return None
        return self._data[self._keys[pos - 1]]

    def ceiling(self, key: _KT) -> _VT | None:
        """
        Returns the value associated with the smallest key >= the given key,
        or None if there is no such key.
        """
        pos = bisect_left(self._keys, key)
        if pos == len(self._keys):
            return None
        return self._data[self._keys[pos]]

    def lower(self, key: _KT) -> _VT | None:
        """
        Returns the value associated with the greatest key < the given key,
        or None if there is no such key.
        """
        pos = bisect_left(self._keys, key)
        if pos == 0:
            return None
        return self._data[self._keys[pos - 1]]

    def higher(self, key: _KT) -> _VT | None:
        """
        Returns the value associated with the smallest key > the given key,
        or None if there is no such key.
        """
        pos = bisect_right(self._keys, key)
        if pos == len(self._keys):
            return None
        return self._data[self._keys[pos]]

    def keys(self) -> KeysView[_KT]:
        """Return a view of the sorted keys."""
        return self._data.keys()

    def values(self) -> ValuesView[_VT]:
        """Return a view of the values in key order."""
        return self._data.values()

    def items(self) -> ItemsView[_KT, _VT]:
        """Return a view of (key, value) pairs in key order."""
        return self._data.items()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({dict(self._data)!r})"

    def copy(self) -> "LookupDict[_KT, _VT]":
        """Return a shallow copy of the LookupDict."""
        return LookupDict(dict(self._data))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LookupDict):
            return dict(self._data) == dict(other._data)
        if isinstance(other, Mapping):
            return dict(self._data) == dict(other)
        return NotImplemented
