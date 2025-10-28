import re
from typing import Any

from linkgen.structures import ReadonlyDict
from linkgen.utils import io_util


def _compile(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Failed to compile regex pattern '{pattern}': {e}") from e


def _precompile_patterns(
    pattern_mapping: dict[str, str | list[str]],
) -> ReadonlyDict[str, re.Pattern[str] | list[re.Pattern[str]]]:
    """
    Load and compile regex patterns from Pattern.json.
    Returns:
        LookupDict[str, re.Pattern[str] | list[re.Pattern[str]]]:
            A mapping from pattern names to compiled regex patterns.
    Raises:
        ValueError: If a pattern entry is empty.
        TypeError: If a pattern entry is not a string or list of strings.
    """
    mapping: dict[str, re.Pattern[str] | list[re.Pattern[str]]] = {}

    for name, values in pattern_mapping.items():
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


def _parse_config() -> ReadonlyDict[str, Any]:
    """
    Load and parse the config.toml file.
    """
    conf = io_util.load_resource_toml("config.toml")

    # load mapping files
    mapping_files: list[str] = conf["mapping"]["files"]
    for file in mapping_files:
        mapping = io_util.load_resource_json(file)
        key = file.removesuffix(".json")
        conf[key] = mapping

    return ReadonlyDict(conf)


# Use the readonly LookupDict
config = _parse_config()
patterns = _precompile_patterns(config["pattern_mapping"])
