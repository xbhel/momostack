"""
Benchmarking module for hyperlink recognition performance testing.

This module provides comprehensive benchmarking capabilities for measuring
the performance of text processing functions, including timing, memory usage,
and CPU utilization metrics.
"""

import argparse
import logging
import os
import statistics
import sys
import timeit
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any, Final

import psutil

from utils import io_util

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_REPEAT: Final = 10
DEFAULT_NUMBER: Final = 1
SOURCE_FILE_DIR: Final = f"{io_util.WORKING_DIR}/../../../samples"


@dataclass
class BenchmarkResult:
    """Container for benchmark results with comprehensive metrics."""

    function_name: str
    repeat_count: int
    number_per_repeat: int
    times: list[float]
    memory_rss_mb: float
    memory_vms_mb: float
    cpu_percent: float

    @property
    def avg_time(self) -> float:
        """Average execution time per call."""
        return statistics.mean(self.times) / self.number_per_repeat

    @property
    def min_time(self) -> float:
        """Minimum execution time per call."""
        return min(self.times) / self.number_per_repeat

    @property
    def max_time(self) -> float:
        """Maximum execution time per call."""
        return max(self.times) / self.number_per_repeat

    @property
    def std_dev(self) -> float:
        """Standard deviation of execution times."""
        if len(self.times) > 1:
            return statistics.stdev(self.times) / self.number_per_repeat
        return 0.0

    @property
    def median_time(self) -> float:
        """Median execution time per call."""
        return statistics.median(self.times) / self.number_per_repeat


def load_test_sources(source_dir: str = SOURCE_FILE_DIR) -> Iterable[tuple[str, Path]]:
    source_path = Path(source_dir)

    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_dir}")

    logger.info(f"Loading test sources from: {source_path.resolve()}")

    for path in io_util.iter_files(source_dir):
        try:
            filesize = path.stat().st_size
            logger.info(f"Loading source: {path.name} ({filesize:,} bytes)")

            # Try different encodings to handle various file types
            encodings = [None, 'utf-8']
            text = None

            for encoding in encodings:
                try:
                    with open(path, encoding=encoding) as f:
                        text = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if text is None:
                logger.warning(
                    f"Could not decode file {path.name} with any supported encoding"
                )
                continue

            yield text, path

        except OSError:
            logger.exception(f"Error reading file {path.name}")
            continue


def benchmark(
    func: Callable[..., Any],
    repeat: int = DEFAULT_REPEAT,
    number: int = DEFAULT_NUMBER,
    warmup: bool = True,
    *args: Any,
    **kwargs: Any,
) -> BenchmarkResult:
    """
    Benchmark a function with comprehensive performance metrics.

    Args:
        func: Function to benchmark
        repeat: Number of times to repeat the benchmark
        number: Number of function calls per repeat
        warmup: Whether to perform a warmup run before benchmarking
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        BenchmarkResult containing all performance metrics

    Raises:
        RuntimeError: If benchmark execution fails
    """
    logger.info(f"Benchmarking function: {func.__name__}")
    logger.info(f"Parameters: repeat={repeat}, number={number}, warmup={warmup}")

    try:
        process = psutil.Process(os.getpid())

        # Perform warmup run to ensure consistent results
        if warmup:
            logger.debug("Performing warmup run...")
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Warmup run failed: {e}")

        # Measure memory before benchmark
        mem_before = process.memory_info()

        # Create timer and run benchmark
        timer = timeit.Timer(lambda: func(*args, **kwargs))
        times = timer.repeat(repeat=repeat, number=number)

        # Measure memory and CPU after benchmark
        mem_after = process.memory_info()
        cpu_percent = process.cpu_percent(interval=0.1)

        # Calculate memory usage (use peak memory if available)
        memory_rss = max(mem_before.rss, mem_after.rss)
        memory_vms = max(mem_before.vms, mem_after.vms)

        result = BenchmarkResult(
            function_name=func.__name__,
            repeat_count=repeat,
            number_per_repeat=number,
            times=times,
            memory_rss_mb=memory_rss / 1024**2,
            memory_vms_mb=memory_vms / 1024**2,
            cpu_percent=cpu_percent,
        )

        logger.info(f"Benchmark completed successfully for {func.__name__}")
    except Exception as e:
        logger.exception(f"Benchmark failed for {func.__name__}")
        raise RuntimeError(f"Benchmark execution failed: {e}") from e
    else:
        return result


def format_benchmark_result(
    result: BenchmarkResult, source_name: str | None = None
) -> str:
    output = []
    output.append("=" * 60)
    output.append("BENCHMARK RESULTS")
    output.append("=" * 60)

    if source_name:
        output.append(f"Source File: {source_name}")
        output.append("-" * 60)

    output.append(f"Function: {result.function_name}")
    output.append(
        f"Configuration: {result.repeat_count} repeats, "
        f"{result.number_per_repeat} calls per repeat"
    )
    output.append("")

    # Timing statistics
    output.append("TIMING STATISTICS:")
    output.append(f"  Average: {result.avg_time:.6f} seconds")
    output.append(f"  Median:  {result.median_time:.6f} seconds")
    output.append(f"  Minimum: {result.min_time:.6f} seconds")
    output.append(f"  Maximum: {result.max_time:.6f} seconds")
    output.append(f"  Std Dev: {result.std_dev:.6f} seconds")
    output.append("")

    # Memory statistics
    output.append("MEMORY USAGE:")
    output.append(f"  RSS (Resident Set Size): {result.memory_rss_mb:.2f} MB")
    output.append(f"  VMS (Virtual Memory Size): {result.memory_vms_mb:.2f} MB")
    output.append("")

    # CPU statistics
    output.append("CPU USAGE:")
    output.append(f"  CPU Percentage: {result.cpu_percent:.2f}%")
    output.append("")

    return "\n".join(output)


def run_benchmarks(
    func: Callable[..., Any],
    repeat: int = DEFAULT_REPEAT,
    number: int = DEFAULT_NUMBER,
    warmup: bool = True,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Run benchmarks on all test sources for the specified function.
    """
    logger.info(f"Starting benchmark suite for function: {func.__name__}")

    try:
        result = benchmark(func, repeat, number, warmup, *args, **kwargs)
        print(format_benchmark_result(result))
    except Exception:
        logger.exception("Benchmark suite failed")
        sys.exit(1)

    logger.info("Benchmark suite completed.")


def main() -> None:
    # CLI: PYTHONPATH=src python src/benchmark/benchmark.py --help

    epilog = dedent("""
    Examples:
        python benchmark.py                           # Run with default settings
        python benchmark.py --repeat 20               # Run 20 repeats per test
        python benchmark.py --sources /path/to/files  # Use custom source directory
        python benchmark.py --no-warmup               # Skip warmup runs
        python benchmark.py --function recognition.extractor.extract_entities
    """)

    """Main entry point for the benchmark script."""
    parser = argparse.ArgumentParser(
        description="Benchmark hyperlink recognition performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "--sources",
        default=SOURCE_FILE_DIR,
        help=f"Directory containing test source files (default: {SOURCE_FILE_DIR})",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=DEFAULT_REPEAT,
        help=f"Number of times to repeat each benchmark (default: {DEFAULT_REPEAT})",
    )
    parser.add_argument(
        "--number",
        type=int,
        default=DEFAULT_NUMBER,
        help=f"Number of function calls per repeat (default: {DEFAULT_NUMBER})",
    )
    parser.add_argument(
        "--no-warmup", action="store_true", help="Skip warmup runs before benchmarking"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--function",
        help="Function to benchmark (e.g., 'recognition.extractor.extract_entities'). "
        "If not specified, uses the default function.",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Parse function if provided
    func_to_benchmark = None
    if args.function:
        try:
            # Parse module.function format
            if '.' in args.function:
                module_path, func_name = args.function.rsplit('.', 1)
                module = __import__(module_path, fromlist=[func_name])
                func_to_benchmark = getattr(module, func_name)
            else:
                # Try to import from current module or built-ins
                func_to_benchmark = globals().get(args.function)
                if func_to_benchmark is None:
                    logger.exception(f"Function '{args.function}' not found")
                    sys.exit(1)
        except (ImportError, AttributeError):
            logger.exception(f"Failed to import function '{args.function}'")
            sys.exit(1)

    if func_to_benchmark is None:
        from recognition.extractor import extract_entities

        func_to_benchmark = extract_entities

    for text, _ in load_test_sources(args.sources):
        # Run benchmarks
        run_benchmarks(
            func=func_to_benchmark,
            repeat=args.repeat,
            number=args.number,
            warmup=not args.no_warmup,
            text=text,
        )


if __name__ == "__main__":
    main()
