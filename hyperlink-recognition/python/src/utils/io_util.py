import inspect
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Robustly resolve the working directory, even if __file__ is unavailable
try:
    WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Fallback for environments where __file__ is not defined
    WORKING_DIR = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))


def load_resource_json(relative_path: str) -> Any:
    normal_path = os.path.normpath(f"../resources/{relative_path}")
    real_path = os.path.join(WORKING_DIR, normal_path)
    with open(real_path, encoding='utf-8') as f:
        try:
            return json.loads(f.read())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error loading JSON schema from {real_path}") from e


def iter_files(base_path: str) -> Iterator[Path]:
    p = Path(base_path)
    if p.is_file():
        yield p
    elif p.is_dir():
        yield from filter(Path.is_file, p.rglob("*"))


def iter_dirs(base_path: str) -> Iterator[Path]:
    yield from filter(Path.is_dir, Path(base_path).rglob("*"))
