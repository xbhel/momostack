# Dynamic SQL WHERE Clause Builder

This feature provides a safe, extensible, and configurable dynamic SQL WHERE clause builder for applications. It allows developers and business users to define complex query conditions using a simple JSON or dictionary configuration, eliminating the need to manually concatenate SQL strings.

**Key Features:**

- Dynamic Condition Building: Supports generating a SQL WHERE clause dynamically based on an input configuration list.

- SQL Injection Prevention: The core implementation integrates with SQLAlchemy, automatically binding values as parameters to fundamentally prevent SQL injection risks.

- Nested Logic Support: Capable of handling arbitrarily nested AND and OR combinations to construct complex query logic.

- Rich Operator Support: Supports common comparison operators (=, !=, >, <) as well as special conditions like IN and IS NULL.

## Architectural Decision Record (ADR)

ADR-001: Why SQLAlchemy Expressions Instead of Raw SQL Strings?

Decision: We have decided to build SQLAlchemy ClauseElement expression objects instead of generating raw SQL strings directly.

Reasons:

Security: Direct SQL string concatenation is vulnerable to severe SQL injection attacks. Using SQLAlchemy expressions ensures that all values are automatically parameterized, securing the queries.

Compatibility: SQLAlchemy expressions can be compiled into SQL for various database dialects (e.g., PostgreSQL, SQLite, MySQL), improving code portability.

Composability: SQLAlchemy expressions are composable, allowing our builder to easily handle complex nested AND/OR logic and integrate seamlessly with other SQLAlchemy query components.

## API List
Class: WhereClauseBuilder
Description: The core builder class that converts a configuration into a SQLAlchemy expression.

Method: `build(self, config: List[Any]) -> Optional[ClauseElement]`
Description: Recursively constructs a SQLAlchemy query expression based on the provided configuration.

Parameters:

config (List[Any]): A list of dictionaries representing the conditions and combiners.

Return Value:

Optional[ClauseElement]: Returns a SQLAlchemy expression on success; returns None if the configuration is empty.

### Operator

- eq: `= $val`
- lt: `< $val`
- gt: `> $val`
- ne: `!=, <> $val`
- ge: `>= $val`
- le: `<= $val`
- in: `in ($val1, $val2)`
- not in: `not in ($val1, $val2)`
- between: `between $val1 and $val2`
- like: `like $val`
- not like: `not like $val`
- is: `is NULL`
- is not: `is not NULL`
- startswith: `startwith(column, $val)`
- endswith:  `endswith(column, $val)`

## Examples
Example 1: Simple AND Condition

```python
config1 = [
    {'column': 'region', 'operator': 'eq', 'value': 'AU'},
    {'column': 'country', 'operator': 'ne', 'value': 'CN'}
]

where_clause = builder.build(config1)
# Corresponding SQL: WHERE region = 'AU' AND country != 'CN'
```

Example 2: Complex OR and IN Conditions

```python
config2 = [
    {
        'combiner': 'OR',
        'conditions': [
            {'column': 'region', 'operator': 'eq', 'value': 'AU'},
            {'column': 'country', 'operator': 'in', 'value': ['US', 'CN', 'UK']},
            {'column': 'user_name', 'operator': 'eq', 'value': None}
        ]
    }
]

where_clause = builder.build(config2)
# Corresponding SQL: WHERE (region = 'AU' OR country IN ('US', 'CN', 'UK') OR user_name IS NULL)
```

Example 3: Mixed AND and OR

```python
config3 = [
    {'column': 'user_id', 'operator': 'eq', 'value': 100},
    {
        'combiner': 'OR',
        'conditions': [
            {'column': 'region', 'operator': 'eq', 'value': 'AU'},
            {'column': 'country', 'operator': 'eq', 'value': 'CN'}
        ]
    }
]

where_clause = builder.build(config3)
# Corresponding SQL: WHERE user_id = 100 AND (region = 'AU' OR country = 'CN')
```

## Roadmap 
- Extend Operators: Add support for more complex SQL operators like LIKE, BETWEEN, and EXISTS.

- Error Handling: Improve input validation to provide more user-friendly error messages for invalid or missing configuration fields.

- ORM Model Integration: Consider adding an option to use ORM models (e.g., User.region) as direct input.

- Performance Testing: Conduct performance tests with large-scale configurations to ensure builder efficiency.

- Documentation: Add more detailed docstrings for all methods and classes, along with comprehensive type hints.

## References

- [SQLAlchemy Operator](https://docs.sqlalchemy.org/en/20/core/operators.html)