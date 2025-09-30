# Benchmark

Benchmarking module [benchmark.py](../python/linkgen/src/benchmark/benchmark.py) for hyperlink recognition performance testing.

This module provides comprehensive benchmarking capabilities for measuring
the performance of text processing functions, including timing, memory usage,
and CPU utilization metrics.

## Extractor benchmark

Automatically extract potential references in legal documents and extract relevant contextual attributes to support hyperlink recognition.

```
The Civil Code of the People's Republic of China.htm (688,933 bytes)

TIMING STATISTICS:
  Average: 0.204605 seconds
  Median:  0.203886 seconds
  Minimum: 0.195436 seconds
  Maximum: 0.211556 seconds
  Std Dev: 0.005061 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 42.88 MB
  VMS (Virtual Memory Size): 29.58 MB

CPU USAGE:
  CPU Percentage: 0.00%
```

```
Source: The Civil Code of the People's Republic of China.xml (3,181,211 bytes)

TIMING STATISTICS:
  Average: 0.756844 seconds
  Median:  0.742604 seconds
  Minimum: 0.721399 seconds
  Maximum: 0.861399 seconds
  Std Dev: 0.039365 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 47.27 MB
  VMS (Virtual Memory Size): 33.84 MB

CPU USAGE:
  CPU Percentage: 0.00%
```


### Feature - Handle continuous case numbers and articles

```
The Civil Code of the People's Republic of China.htm (688,933 bytes)

TIMING STATISTICS:
  Average: 0.237035 seconds
  Median:  0.236746 seconds
  Minimum: 0.228226 seconds
  Maximum: 0.249577 seconds
  Std Dev: 0.007467 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 46.14 MB
  VMS (Virtual Memory Size): 32.66 MB

CPU USAGE:
  CPU Percentage: 0.00%
```

```
Source: The Civil Code of the People's Republic of China.xml (3,181,211 bytes)

TIMING STATISTICS:
  Average: 0.857323 seconds
  Median:  0.850761 seconds
  Minimum: 0.808973 seconds
  Maximum: 0.961474 seconds
  Std Dev: 0.044131 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 50.50 MB
  VMS (Virtual Memory Size): 37.05 MB

CPU USAGE:
  CPU Percentage: 0.00%
```

Related to:

- [CaseNoExtractor](../python/linkgen/src/linkgen/extractor.py)
- [LawArticleExtractor](../python/linkgen/src/linkgen/extractor.py)


### Feature - Update regex for case numbers and articles

```
The Civil Code of the People's Republic of China.htm (688,933 bytes)

TIMING STATISTICS:
  Average: 0.188554 seconds
  Median:  0.189565 seconds
  Minimum: 0.179436 seconds
  Maximum: 0.196664 seconds
  Std Dev: 0.006029 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 45.49 MB
  VMS (Virtual Memory Size): 32.02 MB

CPU USAGE:
  CPU Percentage: 0.00%
```

```
Source: The Civil Code of the People's Republic of China.xml (3,181,211 bytes)

TIMING STATISTICS:
  Average: 0.729557 seconds
  Median:  0.721545 seconds
  Minimum: 0.680572 seconds
  Maximum: 0.819960 seconds
  Std Dev: 0.039173 seconds

MEMORY USAGE:
  RSS (Resident Set Size): 49.80 MB
  VMS (Virtual Memory Size): 36.31 MB

CPU USAGE:
```

Related to:

- [PatternMapping](../python/linkgen/src/linkgen/resources/PatternMapping.json)