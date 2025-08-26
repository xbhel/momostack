
from dataclasses import dataclass
from typing import Any, Self


@dataclass
class ConditionExp:
    """
    (region, "=|eq", 'AU') => region = 'AU'
    (region, "=|eq|in", ['AU', 'CN']) => region in ('AU', 'CN')
    (region, "=|eq|in", ['AU']) => region = 'AU'
    (region, "!=|!eq|!in", ['AU']) => region != 'AU'
    eq
    lt
    gt
    ne
    ge
    le
    in
    not in
    between
    like
    not like
    is
    is not
    startswith
    endswith
    """
    column: str
    operator: str
    value: Any

class ConditionCombiner:
    """
    ('or', [(region, "=", 'AU'), (country, "=", 'CN')]) => or (region='AU' and country='CN')
    """
    combiner: str
    conditions: list[ConditionExp | Self]



class WhereBuilder:
    pass
