# Regex Optimization Guide

Regular expressions are powerful, but poorly written patterns can cause severe performance problems such as **catastrophic backtracking** and even **ReDoS** (Regular Expression Denial of Service). This guide summarizes common optimization techniques, before-and-after examples, and benchmarking methods to help you write safer and faster regex.

##  Principles

- Avoid catastrophic backtracking — prevent patterns that trigger exponential attempts
- Be precise — narrow down the match scope to reduce ambiguity
- Reduce overhead — use non-capturing groups, precompile regex, reuse patterns
- Prioritize readability — split overly complex regex, use alternatives if needed

## Common Optimization

- Avoid catastrophic backtracking

```
❌ (a+)+$     # exponential backtracking
✅ a+$        # linear
```

- Capturing vs Non-capturing groups

```
❌ (foo|bar|baz)
✅ (?:foo|bar|baz)
```

- Use anchors

```
❌ abc
✅ ^abc$
```

- Prefer character classes

```
❌ (a|b|c|d)
✅ [abcd]
```

- Avoid greedy `.*`

```
❌ <.*>
✅ <[^>]*>
```

- Numeric ranges

```
❌ [0123456789]
✅ [0-9]
```

- Precompile regex

```python
❌ re.match(r"\d+", s)
✅ compiled = re.compile(r"\d+"); compiled.match(s)
```

- Split complex regex

```
❌ (\w+)://([\w.]+)/(\S+)
✅ ^\w+   # scheme
   [\w.]+ # host
   /\S+$  # path
```

## Common ReDoS Pitfalls

- Alternation with overlapping prefixes

```python
# Causes heavy backtracking with input like `"a"*1000 + "b"`.
❌ (a|aa)+ 

# Merges quantifiers, no backtracking.
✅ aa*+
```

- Greedy ambiguous repetition

```python
# On `"a"*1000 + "b"`, triggers exponential backtracking.
❌ (.*a){10}

# Explicitly excludes irrelevant chars, avoids backtracking.
✅ (?:[^a]*a){10}
```

- Nested quantifiers

```python
# On "1"*1000 + "x", catastrophic backtracking occurs.
❌ (\d+)+

# Equivalent logic, no nested quantifiers.
✅ \d+
```

- Overly permissive wildcards

```python
# Greedy matching, poor performance on long inputs.
❌ .*=.* 

# More precise, prevents unnecessary backtracking.
✅ [^=]+=[^=]+
```

## Benchmarking in Python

```python
import re, timeit

setup = "import re; text = 'a'*1000 + 'b'"
stmt1 = "re.match(r'(a+)+$', text)"
stmt2 = "re.match(r'a+$', text)"

print("Bad:", timeit.timeit(stmt1, setup=setup, number=100))
print("Good:", timeit.timeit(stmt2, setup=setup, number=100))
```

## Recommended Tools

- [Regex101](https://regex101.com/?utm_source=chatgpt.com) — debug and explain regex
- [Debuggex](https://www.debuggex.com/?utm_source=chatgpt.com) — visualize regex execution
- [MeasureThat](https://measurethat.net) — online regex performance benchmark
- [RegexBuddy](https://www.regexbuddy.com) — desktop tool with advanced analysis