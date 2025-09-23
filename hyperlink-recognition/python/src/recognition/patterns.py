import re

from structures import ReadonlyDict
from utils import io_util


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
