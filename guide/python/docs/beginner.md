# Python Notes

A comprehensive reference guide for common Python patterns, best practices, and advanced concepts. This document covers practical examples and real-world usage patterns that every Python developer should know.

Useful links:

- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

## Table of Contents

- [Python Notes](#python-notes)
  - [Table of Contents](#table-of-contents)
  - [Merging Dictionaries](#merging-dictionaries)
    - [Methods Comparison](#methods-comparison)
    - [Key Points](#key-points)
  - [Deque vs List](#deque-vs-list)
    - [Performance Characteristics](#performance-characteristics)
    - [When to Use Each](#when-to-use-each)
  - [NamedTuple Instead of Tuple](#namedtuple-instead-of-tuple)
    - [Basic Usage](#basic-usage)
    - [Advanced Features](#advanced-features)
    - [Key Benefits](#key-benefits)
    - [When to Use Alternatives](#when-to-use-alternatives)
  - [Context Managers](#context-managers)
    - [__enter__/__exit__ Pattern](#enterexit-pattern)
    - [Key Implementation Points](#key-implementation-points)
    - [`@contextmanager` Decorator](#contextmanager-decorator)
      - [Common Patterns](#common-patterns)
      - [Handling Exceptions](#handling-exceptions)
    - [When to Use Each Approach](#when-to-use-each-approach)
    - [Decision Matrix](#decision-matrix)
    - [Best Practices](#best-practices)
  - [__init\_subclass__ Method](#init_subclass-method)
    - [Basic Usage](#basic-usage-1)
    - [Abstract Factory Design Pattern](#abstract-factory-design-pattern)
    - [Validation and Configuration](#validation-and-configuration)
    - [Plugin System](#plugin-system)
    - [Key Points and Best Practices](#key-points-and-best-practices)
    - [Common Use Cases](#common-use-cases)

---

## Merging Dictionaries

Python provides several ways to merge dictionaries, with the union operator `|` being the most modern approach.

### Methods Comparison

```python
from typing import Dict, Any

# Method 1: Copy and update (works in all Python versions)
def merge_copy_update(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries using copy() and update()."""
    result = d1.copy()
    result.update(d2)
    return result

# Method 2: Dictionary unpacking (Python 3.5+)
def merge_unpacking(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries using unpacking syntax."""
    return {**d1, **d2}

# Method 3: Union operator (Python 3.9+)
def merge_union(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries using the union operator."""
    return d1 | d2

# Method 4: In-place update (Python 3.9+)
def merge_inplace(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge dictionaries in-place using |= operator."""
    d1 |= d2
    return d1

# Example usage
base_config = {"host": "localhost", "port": 8080}
user_config = {"port": 3000, "debug": True}

merged = base_config | user_config
print(merged)  # {'host': 'localhost', 'port': 3000, 'debug': True}
```

### Key Points

- **Behavior**: Keys in the second dictionary override keys in the first
- **Python version**: `|` and `|=` operators require Python 3.9 or newer
- **Performance**: Union operator is generally the fastest for simple merges
- **Immutability**: Union operator creates a new dictionary; `|=` modifies in-place

---

## Deque vs List

Understanding when to use `collections.deque` versus `list` is crucial for writing efficient Python code.

### Performance Characteristics

```python
from collections import deque
from typing import List, Deque

# List: Array-backed, efficient for end operations
numbers_list: List[int] = [1, 2, 3]
numbers_list.append(4)        # O(1) - efficient
numbers_list.pop()            # O(1) - efficient
numbers_list.insert(0, 0)     # O(n) - expensive!
numbers_list.pop(0)           # O(n) - expensive!

# Deque: Double-ended queue, efficient for both ends
numbers_deque: Deque[int] = deque([1, 2, 3])
numbers_deque.append(4)       # O(1) - efficient
numbers_deque.pop()           # O(1) - efficient
numbers_deque.appendleft(0)   # O(1) - efficient!
numbers_deque.popleft()       # O(1) - efficient!

# Example: Queue implementation
class Queue:
    def __init__(self):
        self._items = deque()
    
    def enqueue(self, item):
        self._items.append(item)
    
    def dequeue(self):
        return self._items.popleft()
    
    def is_empty(self):
        return len(self._items) == 0
```

### When to Use Each

| Use Case                     | Data Structure | Reason                         |
| ---------------------------- | -------------- | ------------------------------ |
| Random access by index       | `list`         | O(1) indexing, slicing support |
| Frequent append/pop at end   | `list`         | Optimized for end operations   |
| Queue/stack patterns         | `deque`        | O(1) operations at both ends   |
| Frequent left-end operations | `deque`        | Avoids O(n) list operations    |
| Memory efficiency            | `list`         | Lower memory overhead          |
| Thread-safe operations       | `deque`        | Atomic append/pop operations   |

---

## NamedTuple Instead of Tuple

`NamedTuple` provides a clean way to create structured data with named fields, type hints, and immutability.

### Basic Usage

```python
from typing import NamedTuple
from collections import namedtuple

# Modern approach: typing.NamedTuple (recommended)
class Point(NamedTuple):
    """A 2D point with x and y coordinates."""
    x: int
    y: int = 0  # default value

class User(NamedTuple):
    """User information with required fields."""
    id: int
    name: str
    email: str = ""  # optional field with default
    is_active: bool = True

# Usage examples
point = Point(3)  # y defaults to 0
print(f"Point: ({point.x}, {point.y})")  # Point: (3, 0)
print(f"Index access: {point[0]}, {point[1]}")  # Index access: 3, 0

# Tuple unpacking works
x, y = point
print(f"Unpacked: x={x}, y={y}")

# Immutability
# point.x = 10  # AttributeError: NamedTuple instances are immutable

# Legacy approach: collections.namedtuple
LegacyUser = namedtuple("LegacyUser", ["id", "name", "email"])
legacy_user = LegacyUser(1, "Alice", "alice@example.com")
print(f"Legacy user: {legacy_user.name}")  # No type hints available
```

### Advanced Features

```python
from typing import NamedTuple, Optional

class DatabaseConfig(NamedTuple):
    """Database configuration with validation."""
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_enabled: bool = False
    
    def connection_string(self) -> str:
        """Generate database connection string."""
        ssl = "?sslmode=require" if self.ssl_enabled else ""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}{ssl}"
    
    def __str__(self) -> str:
        return f"DatabaseConfig(host='{self.host}', port={self.port})"

# Usage
config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="myapp",
    username="user",
    password="secret",
    ssl_enabled=True
)

print(config.connection_string())
print(config)  # Uses custom __str__ method
```

### Key Benefits

- **Type Safety**: Full type hint support with mypy/pylint
- **Readability**: Named fields instead of magic indices
- **Immutability**: Prevents accidental modifications
- **Memory Efficient**: Same memory footprint as regular tuples
- **Compatibility**: Works with tuple unpacking and indexing
- **Methods**: Can define custom methods and properties

### When to Use Alternatives

- **`dataclasses.dataclass`**: When you need mutability or complex initialization
- **`pydantic.BaseModel`**: When you need validation and serialization
- **Regular `tuple`**: For simple, temporary data where names don't matter

---

## Context Managers

Context managers ensure proper resource management by automatically handling setup and cleanup operations. They're essential for working with files, database connections, locks, and other resources.

### __enter__/__exit__ Pattern

Create context managers by implementing `__enter__` and `__exit__` methods. This approach gives you full control over the context lifecycle.

```python
from typing import Optional, TextIO

class FileManager:
    """Context manager for file operations with automatic cleanup."""
    
    def __init__(self, filename: str, mode: str = "r", encoding: str = "utf-8"):
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
        self.file: Optional[TextIO] = None

    def __enter__(self) -> TextIO:
        """Setup: Open the file and return it for use in the with-block."""
        self.file = open(self.filename, self.mode, encoding=self.encoding)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Cleanup: Close the file and handle exceptions."""
        if self.file:
            self.file.close()
        
        # Handle specific exceptions if needed
        if exc_type is FileNotFoundError:
            print(f"Warning: File {self.filename} not found")
            return True  # Suppress the exception
        
        # Return False to propagate exceptions, True to suppress
        return False

# Usage examples
with FileManager("data.txt", "r") as f:
    content = f.read()
    print(f"File contains {len(content)} characters")

# Exception handling example
with FileManager("nonexistent.txt") as f:
    content = f.read()  # FileNotFoundError will be suppressed
```

### Key Implementation Points

- **`__enter__`**: Setup resources and return the object to use in the `with` block
- **`__exit__`**: Cleanup resources; receives exception info if an exception occurred
- **Exception handling**: Return `True` to suppress exceptions, `False`/`None` to propagate
- **Resource safety**: Always ensure cleanup happens, even if exceptions occur

### `@contextmanager` Decorator

Create lightweight context managers using a generator-style function. This approach is ideal for simple setup/teardown scenarios.

```python
from contextlib import contextmanager
from typing import Generator, TextIO

@contextmanager
def managed_resource() -> Generator[str, None, None]:
    """Example of a basic context manager using @contextmanager."""
    # Setup phase
    resource = acquire_resource()
    try:
        yield resource  # Hand control to the with-block
    finally:
        # Cleanup phase - always runs
        release_resource(resource)

# Usage
with managed_resource() as resource:
    # Use the resource here
    process_resource(resource)
```

#### Common Patterns

```python
from contextlib import contextmanager
from typing import Generator, TextIO, Iterator
import time
import os

# Pattern 1: File operations with custom encoding
@contextmanager
def open_text(path: str, encoding: str = "utf-8") -> Generator[TextIO, None, None]:
    """Open a text file with guaranteed cleanup."""
    f = open(path, mode="r", encoding=encoding)
    try:
        yield f
    finally:
        f.close()

# Pattern 2: Performance timing
@contextmanager
def timer(label: str = "Operation") -> Generator[None, None, None]:
    """Time the execution of a code block."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"{label}: {elapsed:.6f} seconds")

# Pattern 3: Temporary directory
@contextmanager
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory and clean it up."""
    import tempfile
    temp_path = tempfile.mkdtemp()
    try:
        yield temp_path
    finally:
        import shutil
        shutil.rmtree(temp_path)

# Pattern 4: Line-by-line file processing
@contextmanager
def open_lines(path: str, encoding: str = "utf-8") -> Generator[Iterator[str], None, None]:
    """Open a file and yield lines without newline characters."""
    f = open(path, "r", encoding=encoding)
    try:
        yield (line.rstrip("\n") for line in f)
    finally:
        f.close()

# Usage examples
with timer("File processing"):
    with open_text("data.txt") as f:
        content = f.read()
        print(f"Read {len(content)} characters")

with temp_dir() as temp_path:
    # Create files in temporary directory
    with open(os.path.join(temp_path, "test.txt"), "w") as f:
        f.write("Hello, World!")
    # Directory is automatically cleaned up

with open_lines("config.txt") as lines:
    for line in lines:
        if line.startswith("#"):
            continue
        print(f"Config: {line}")
```

#### Handling Exceptions

Context managers can catch, transform, or suppress exceptions that occur within the `with` block.

```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def suppress_not_found() -> Generator[None, None, None]:
    """Suppress FileNotFoundError exceptions."""
    try:
        yield
    except FileNotFoundError:
        pass  # Silently ignore file not found errors

@contextmanager
def translate_value_error() -> Generator[None, None, None]:
    """Transform ValueError to RuntimeError with context."""
    try:
        yield
    except ValueError as err:
        raise RuntimeError(f"Invalid value provided: {err}") from err

@contextmanager
def retry_on_failure(max_retries: int = 3) -> Generator[None, None, None]:
    """Retry operations that might fail."""
    for attempt in range(max_retries):
        try:
            yield
            return  # Success, exit the context manager
        except Exception as e:
            if attempt == max_retries - 1:
                raise  # Last attempt failed, re-raise the exception
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")

# Usage examples
with suppress_not_found():
    with open("optional_file.txt") as f:
        content = f.read()  # Won't crash if file doesn't exist

with translate_value_error():
    int("invalid")  # ValueError becomes RuntimeError

with retry_on_failure(max_retries=3):
    # Some operation that might fail
    risky_operation()
```

### When to Use Each Approach

Choose the right approach based on your specific needs:

```python
from contextlib import contextmanager
from typing import Generator

# Use @contextmanager for simple, stateless operations
@contextmanager
def simple_file_operation(path: str) -> Generator[TextIO, None, None]:
    """Simple file operation - perfect for @contextmanager."""
    f = open(path, "r")
    try:
        yield f
    finally:
        f.close()

# Use class-based approach for complex, stateful operations
class DatabaseConnection:
    """Complex database connection with state and methods."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
        self.transaction_count = 0
    
    def __enter__(self) -> "DatabaseConnection":
        """Setup database connection."""
        self.connection = connect_to_database(self.connection_string)
        return self  # Return self to expose methods
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Cleanup database connection."""
        if self.connection:
            if exc_type:  # Exception occurred
                self.rollback()
            else:
                self.commit()
            self.connection.close()
        return False
    
    def execute(self, query: str) -> list:
        """Execute a database query."""
        return self.connection.execute(query)
    
    def begin_transaction(self):
        """Start a new transaction."""
        self.transaction_count += 1
        self.connection.begin()
    
    def commit(self):
        """Commit the current transaction."""
        self.connection.commit()
    
    def rollback(self):
        """Rollback the current transaction."""
        self.connection.rollback()

# Usage comparison
# Simple case - use @contextmanager
with simple_file_operation("data.txt") as f:
    content = f.read()

# Complex case - use class-based approach
with DatabaseConnection("postgresql://localhost/mydb") as db:
    db.begin_transaction()
    result = db.execute("SELECT * FROM users")
    # Transaction is automatically committed or rolled back
```

### Decision Matrix

| Scenario                 | Use `@contextmanager` | Use Class-Based |
| ------------------------ | --------------------- | --------------- |
| Simple setup/cleanup     | ✅                     | ❌               |
| Stateless operations     | ✅                     | ❌               |
| One-time resource        | ✅                     | ❌               |
| Complex state management | ❌                     | ✅               |
| Multiple methods needed  | ❌                     | ✅               |
| Reusable across contexts | ❌                     | ✅               |
| Exception handling logic | ❌                     | ✅               |

### Best Practices

- **Keep it simple**: Use `@contextmanager` unless you need the complexity of a class
- **Minimal setup/teardown**: Keep logic before/after `yield` minimal
- **Exception safety**: Always ensure cleanup happens, even if exceptions occur
- **Resource management**: Always release resources in the cleanup phase
- **State exposure**: Return `self` from `__enter__` when you need to expose methods/state


---

## __init_subclass__ Method

The `__init_subclass__` method is a powerful hook that's called whenever a class is subclassed. It's perfect for implementing class registries, validation systems, and factory patterns without requiring explicit registration.

### Basic Usage

```python
from typing import ClassVar, Dict, Type

class BaseClass:
    """Base class that automatically registers all subclasses."""
    _registry: ClassVar[Dict[str, Type["BaseClass"]]] = {}
    
    def __init_subclass__(cls, **kwargs):
        """Called when a class is subclassed."""
        super().__init_subclass__(**kwargs)
        # Automatically register the subclass
        cls._registry[cls.__name__] = cls
        print(f"✓ Registered subclass: {cls.__name__}")
    
    @classmethod
    def get_subclass(cls, name: str) -> Type["BaseClass"]:
        """Retrieve a registered subclass by name."""
        return cls._registry.get(name)
    
    @classmethod
    def list_subclasses(cls) -> list[str]:
        """List all registered subclass names."""
        return list(cls._registry.keys())

# Subclasses are automatically registered when defined
class ConcreteA(BaseClass):
    """First concrete implementation."""
    pass

class ConcreteB(BaseClass):
    """Second concrete implementation."""
    pass

# Usage
print("Available subclasses:", BaseClass.list_subclasses())
# Output: Available subclasses: ['ConcreteA', 'ConcreteB']

subclass = BaseClass.get_subclass("ConcreteA")
if subclass:
    instance = subclass()
    print(f"Created instance: {instance}")
```

### Abstract Factory Design Pattern

Implement a factory pattern where subclasses are automatically registered and can be created by name.

```python
from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Type

class Animal(ABC):
    """Abstract base class for animals with automatic registration."""
    _registry: ClassVar[Dict[str, Type["Animal"]]] = {}
    
    def __init_subclass__(cls, **kwargs):
        """Register each animal subclass automatically."""
        super().__init_subclass__(**kwargs)
        # Register using lowercase class name as key
        cls._registry[cls.__name__.lower()] = cls
        print(f"🐾 Registered animal: {cls.__name__}")
    
    @classmethod
    def create(cls, animal_type: str, **kwargs) -> "Animal":
        """Factory method to create animals by type name."""
        if animal_type not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown animal type: {animal_type}. Available: {available}")
        return cls._registry[animal_type](**kwargs)
    
    @classmethod
    def list_available(cls) -> list[str]:
        """List all available animal types."""
        return list(cls._registry.keys())
    
    @abstractmethod
    def make_sound(self) -> str:
        """Each animal must implement its sound."""
        pass
    
    @abstractmethod
    def get_species(self) -> str:
        """Each animal must specify its species."""
        pass

class Dog(Animal):
    """A dog implementation."""
    
    def __init__(self, name: str, breed: str = "Mixed"):
        self.name = name
        self.breed = breed
    
    def make_sound(self) -> str:
        return f"{self.name} the {self.breed} says Woof!"
    
    def get_species(self) -> str:
        return "Canis lupus familiaris"

class Cat(Animal):
    """A cat implementation."""
    
    def __init__(self, name: str, is_indoor: bool = True):
        self.name = name
        self.is_indoor = is_indoor
    
    def make_sound(self) -> str:
        return f"{self.name} says Meow!"
    
    def get_species(self) -> str:
        return "Felis catus"

class Bird(Animal):
    """A bird implementation."""
    
    def __init__(self, name: str, can_fly: bool = True):
        self.name = name
        self.can_fly = can_fly
    
    def make_sound(self) -> str:
        return f"{self.name} says Tweet!"
    
    def get_species(self) -> str:
        return "Aves"

# Usage examples
print("Available animals:", Animal.list_available())
# Output: Available animals: ['dog', 'cat', 'bird']

# Create animals using the factory
animals = [
    Animal.create("dog", name="Buddy", breed="Golden Retriever"),
    Animal.create("cat", name="Whiskers", is_indoor=True),
    Animal.create("bird", name="Tweety", can_fly=True)
]

for animal in animals:
    print(f"{animal.make_sound()} (Species: {animal.get_species()})")
```

### Validation and Configuration

Use `__init_subclass__` to validate subclass requirements and set default configurations.

```python
from typing import List, Optional

class ConfigurableBase:
    """Base class that validates configuration requirements."""
    
    def __init_subclass__(cls, required_config: Optional[List[str]] = None, **kwargs):
        """Validate subclass configuration requirements."""
        super().__init_subclass__(**kwargs)
        
        # Validate required configuration attributes
        if required_config:
            missing_configs = []
            for config in required_config:
                if not hasattr(cls, config):
                    missing_configs.append(config)
            
            if missing_configs:
                raise TypeError(
                    f"{cls.__name__} must define the following configuration attributes: "
                    f"{missing_configs}"
                )
        
        # Set default values for common attributes
        if not hasattr(cls, 'version'):
            cls.version = "1.0.0"
        
        if not hasattr(cls, 'enabled'):
            cls.enabled = True
        
        print(f"✓ Configured {cls.__name__} with version {cls.version}")

class Database(ConfigurableBase, required_config=['host', 'port']):
    """Database connection configuration."""
    host = "localhost"
    port = 5432
    database = "default_db"
    
    def connect(self) -> str:
        """Create connection string."""
        return f"postgresql://{self.host}:{self.port}/{self.database}"

class Redis(ConfigurableBase, required_config=['host']):
    """Redis connection configuration."""
    host = "localhost"
    # port not required for Redis (uses default 6379)
    
    def connect(self) -> str:
        """Create Redis connection string."""
        return f"redis://{self.host}:6379"

class Elasticsearch(ConfigurableBase, required_config=['host', 'port', 'index']):
    """Elasticsearch configuration with custom requirements."""
    host = "localhost"
    port = 9200
    index = "default_index"
    version = "8.0.0"  # Override default version
    
    def connect(self) -> str:
        """Create Elasticsearch connection string."""
        return f"http://{self.host}:{self.port}/{self.index}"

# Usage
configs = [Database(), Redis(), Elasticsearch()]
for config in configs:
    print(f"{config.__class__.__name__}: {config.connect()}")
```

### Plugin System

Create a flexible plugin architecture where plugins are automatically discovered and registered.

```python
from typing import ClassVar, Dict, Type, Any, Optional
from abc import ABC, abstractmethod

class PluginBase(ABC):
    """Base class for all plugins with automatic registration."""
    _plugins: ClassVar[Dict[str, Type["PluginBase"]]] = {}
    
    def __init_subclass__(cls, plugin_name: Optional[str] = None, **kwargs):
        """Register plugin with optional custom name."""
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__.lower().replace('processor', '')
        cls._plugins[name] = cls
        print(f"🔌 Registered plugin: {name}")
    
    @classmethod
    def get_plugin(cls, name: str) -> Optional[Type["PluginBase"]]:
        """Retrieve a plugin by name."""
        return cls._plugins.get(name)
    
    @classmethod
    def list_plugins(cls) -> list[str]:
        """List all available plugin names."""
        return list(cls._plugins.keys())
    
    @classmethod
    def create_plugin(cls, name: str, **kwargs) -> "PluginBase":
        """Create a plugin instance by name."""
        plugin_class = cls.get_plugin(name)
        if not plugin_class:
            available = ", ".join(cls.list_plugins())
            raise ValueError(f"Plugin '{name}' not found. Available: {available}")
        return plugin_class(**kwargs)
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data using this plugin."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of what this plugin does."""
        pass

class TextProcessor(PluginBase, plugin_name="text"):
    """Plugin for text processing operations."""
    
    def __init__(self, uppercase: bool = True):
        self.uppercase = uppercase
    
    def process(self, data: str) -> str:
        """Convert text to uppercase or lowercase."""
        return data.upper() if self.uppercase else data.lower()
    
    def get_description(self) -> str:
        return "Text case conversion processor"

class JSONProcessor(PluginBase, plugin_name="json"):
    """Plugin for JSON data processing."""
    
    def __init__(self, pretty_print: bool = False):
        self.pretty_print = pretty_print
    
    def process(self, data: dict) -> str:
        """Convert dictionary to JSON string."""
        import json
        indent = 2 if self.pretty_print else None
        return json.dumps(data, indent=indent)
    
    def get_description(self) -> str:
        return "JSON serialization processor"

class XMLProcessor(PluginBase):
    """Plugin for XML processing (auto-registered as 'xmlprocessor')."""
    
    def process(self, data: dict) -> str:
        """Convert dictionary to XML string."""
        # Simplified XML conversion
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<root>']
        for key, value in data.items():
            xml_parts.append(f'  <{key}>{value}</{key}>')
        xml_parts.append('</root>')
        return '\n'.join(xml_parts)
    
    def get_description(self) -> str:
        return "XML serialization processor"

# Usage examples
print("Available plugins:", PluginBase.list_plugins())
# Output: Available plugins: ['text', 'json', 'xmlprocessor']

# Create and use plugins
text_plugin = PluginBase.create_plugin("text", uppercase=True)
json_plugin = PluginBase.create_plugin("json", pretty_print=True)
xml_plugin = PluginBase.create_plugin("xmlprocessor")

# Process data with different plugins
data = {"name": "Alice", "age": 30}

print("Text processing:", text_plugin.process("hello world"))
print("JSON processing:", json_plugin.process(data))
print("XML processing:", xml_plugin.process(data))

# Get plugin information
for plugin_name in PluginBase.list_plugins():
    plugin = PluginBase.create_plugin(plugin_name)
    print(f"{plugin_name}: {plugin.get_description()}")
```

### Key Points and Best Practices

- **Automatic invocation**: `__init_subclass__` is called for each subclass, not for the base class itself
- **MRO compliance**: Always call `super().__init_subclass__(**kwargs)` to maintain the method resolution order
- **Class variables**: Use `ClassVar` for class-level attributes that should be shared across all subclasses
- **Custom parameters**: Accept custom keyword arguments via `**kwargs` for flexible subclass configuration
- **Registration patterns**: Perfect for automatic class registration, validation systems, and factory patterns
- **Performance**: Registration happens at class definition time, not at runtime
- **Error handling**: Validate subclass requirements early to catch configuration errors immediately

### Common Use Cases

1. **Plugin systems**: Automatically discover and register plugins
2. **Factory patterns**: Create objects by name without explicit registration
3. **Validation frameworks**: Ensure subclasses implement required methods/attributes
4. **Configuration management**: Set default values and validate configuration
5. **ORM systems**: Register model classes for database mapping
6. **Serialization**: Register classes for JSON/XML serialization
