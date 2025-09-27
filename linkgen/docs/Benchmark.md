# Benchmark

Benchmarking module [benchmark.py](../python/src/benchmark/benchmark.py) for hyperlink recognition performance testing.

This module provides comprehensive benchmarking capabilities for measuring
the performance of text processing functions, including timing, memory usage,
and CPU utilization metrics.

## Extractor benchmark

Automatically extract potential references in legal documents and extract relevant contextual attributes to support hyperlink recognition.

```
The Civil Code of the People's Republic of China.htm (688,933 bytes)

TIMING STATISTICS:
  Average: 0.014547 seconds
  Median:  0.014594 seconds
  Minimum: 0.013848 seconds
  Maximum: 0.015219 seconds
  Std Dev: 0.000450 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 41.42 MB
  VMS (Virtual Memory Size): 28.06 MB

CPU USAGE:
  CPU Percentage: 0.00%
```

```
Source: The Civil Code of the People's Republic of China.xml (3,181,211 bytes)

TIMING STATISTICS:
  Average: 0.065786 seconds
  Median:  0.064497 seconds
  Minimum: 0.061637 seconds
  Maximum: 0.072888 seconds
  Std Dev: 0.003848 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 45.73 MB
  VMS (Virtual Memory Size): 32.35 MB

CPU USAGE:
  CPU Percentage: 0.00%
```

