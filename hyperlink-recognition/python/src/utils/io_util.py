import inspect
import json
import os
from typing import Any


def _get_working_dir() -> str:
    # Robustly resolve the working directory, even if __file__ is unavailable
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Fallback for environments where __file__ is not defined
        return os.path.dirname(os.path.abspath(inspect.stack()[0][1]))


def load_schema_json(relative_path: str) -> Any:
    normal_path = os.path.normpath(f"../schemas/{relative_path}")
    real_path = os.path.join(_get_working_dir(), normal_path)
    with open(normal_path, encoding='utf-8') as f:
        try:
            return json.loads(f.read())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error loading JSON schema from {real_path}") from e
