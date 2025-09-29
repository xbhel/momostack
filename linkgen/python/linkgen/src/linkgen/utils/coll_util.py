import json
from collections import defaultdict
from collections.abc import Callable, Iterable
from hashlib import sha256
from typing import Any


def hash_value(value: Any) -> int:
    """Return a deterministic integer hash for arbitrary Python values.

    - For hashable values, use the built-in hash for speed.
    - For common containers, build a normalized, hashable representation:
        dict -> tuple of sorted (key_hash, value_hash)
        list/tuple -> tuple of element hashes
        set/frozenset -> sorted tuple of element hashes
    - Fallback to a stable repr string.
    """

    def normalize(value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float, str, bytes)):
            return value

        if isinstance(value, dict):
            return tuple((k, normalize(v)) for k, v in sorted(value.items()))

        if isinstance(value, (list, tuple, set, frozenset)):
            return tuple(normalize(v) for v in sorted(value))

        return repr(value)

    normalized = normalize(value)
    data = json.dumps(normalized, sort_keys=True, default=str).encode()
    digest = sha256(data).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def reverse_dict[KT, VT](mapping: dict[KT, VT]) -> dict[VT, set[KT]]:
    reversed_mapping: dict[VT, set[KT]] = defaultdict(set)
    for k, v in mapping.items():
        reversed_mapping[v].add(k)
    return reversed_mapping


def group_by[T, K](items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    if not items:
        return {}

    mapping = defaultdict(list)
    for item in items:
        mapping[key(item)].append(item)
    return mapping


def flatten[T](items_list: list[list[T]]) -> list[T]:
    if not items_list:
        return []

    return [item for items in items_list for item in items]


def remove_if[T, K](items: list[T], key: Callable[[T], K]) -> list[T]:
    if not items:
        return []

    write_index = 0
    removed: list[T] = []
    for index in range(len(items)):
        item = items[index]
        if key(item):
            removed.append(item)
        else:
            items[write_index] = item
            write_index += 1

    del items[write_index:]
    return removed
