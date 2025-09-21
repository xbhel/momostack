from collections import defaultdict
from typing import _KT, _VT


def reverse_dict(mapping: dict[_KT, _VT]) -> dict[_VT, set[_KT]]:
    reversed_mapping: dict[_VT, set[_KT]] = defaultdict(set)
    for k, v in mapping.items():
        reversed_mapping[v].add(k)
    return reversed_mapping
