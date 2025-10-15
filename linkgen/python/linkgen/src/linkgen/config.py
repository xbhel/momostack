import re
from typing import Any

from linkgen.structures import ReadonlyDict
from linkgen.utils import io_util


def _compile(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Failed to compile regex pattern '{pattern}': {e}") from e


def _init_patterns() -> ReadonlyDict[str, re.Pattern[str] | list[re.Pattern[str]]]:
    """
    Load and compile regex patterns from Pattern.json.
    Returns:
        LookupDict[str, re.Pattern[str] | list[re.Pattern[str]]]:
            A mapping from pattern names to compiled regex patterns.
    Raises:
        ValueError: If a pattern entry is empty.
        TypeError: If a pattern entry is not a string or list of strings.
    """
    conf = io_util.load_resource_json("PatternMapping.json")
    mapping: dict[str, re.Pattern[str] | list[re.Pattern[str]]] = {}

    for name, values in conf.items():
        if not values:
            raise ValueError(f"Pattern '{name}' is empty.")
        if isinstance(values, list):
            if not all(isinstance(p, str) for p in values):
                raise TypeError(
                    f"Pattern list for '{name}' contains non-string elements."
                )
            mapping[name] = [_compile(pattern) for pattern in values]
        elif isinstance(values, str):
            mapping[name] = _compile(values)
        else:
            raise TypeError(f"Pattern '{name}' must be a string or list of strings.")

    return ReadonlyDict(mapping)


# Use the readonly LookupDict
patterns = _init_patterns()
config: dict[str, Any] = {
    "country_scope": "全国",
    "forward_chinese": "转发",
    "about_chinese": "关于",
    "common_prefixes": ("中华人民共和国", ),
    "ineffective_status": (
        "尚未生效",
        "征求意见稿或草案",
        "To be effective",
        "Draft for comments or Draft",
    ),
    "check_law_abbr_if_suffixes": ("法", ),
    "ignore_law_abbr_if_next": ("制", "务", "令", "规", "律"),
}
