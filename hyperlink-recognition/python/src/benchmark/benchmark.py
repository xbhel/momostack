from collections.abc import Iterable
from time import perf_counter
from typing import Final

from recognition import extractor
from utils import io_util

SOURCE_FILE_DIR: Final = f"{io_util.WORKING_DIR}/../../../samples"


def load_test_sources() -> Iterable[str]:
    for path in io_util.iter_files(SOURCE_FILE_DIR):
        filesize = path.stat().st_size
        print(f"Source: {path.name}, {filesize} bytes")
        try:
            with open(path) as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        yield text


if __name__ == "__main__":
    for text in load_test_sources():
        start = perf_counter()
        result = extractor.extract_entities(text)
        end = perf_counter()

        result_stat = [
            f"{t.name:20}: {len(entities)}" for t, entities in result.items()
        ]
        result_stat_str = "\n".join(result_stat)

        print(f"Elapsed time: {(end - start):9.6f}s")
        print(f"Result stat: \n{result_stat_str}\n")
