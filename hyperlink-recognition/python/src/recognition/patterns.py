import re

from recognition.structures import LookupDict
from utils import io_util

PatternType = re.Pattern[str] | list[re.Pattern[str]]

# Use the readonly LookupDict
patterns: LookupDict[str, PatternType]


def _init_patterns() -> LookupDict[str, PatternType]:
    """
    Load and compile regex patterns from Pattern.json.
    Returns:
        LookupDict[str, PatternType]: A mapping from pattern names to
            compiled regex patterns.
    Raises:
        ValueError: If a pattern entry is empty.
        TypeError: If a pattern entry is not a string or list of strings.
    """
    conf = io_util.load_resource_json("PatternMapping.json")
    mapping: dict[str, PatternType] = {}

    for name, values in conf.items():
        if not values:
            raise ValueError(f"Pattern '{name}' is empty.")
        if isinstance(values, list):
            if not all(isinstance(p, str) for p in values):
                raise TypeError(
                    f"Pattern list for '{name}' contains non-string elements."
                )
            mapping[name] = [re.compile(pattern) for pattern in values]
        elif isinstance(values, str):
            mapping[name] = re.compile(values)
        else:
            raise TypeError(f"Pattern '{name}' must be a string or list of strings.")

    return LookupDict(mapping)


patterns = _init_patterns()
