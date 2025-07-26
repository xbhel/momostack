# 🕸️ TaskFlow

**TaskFlow** is a lightweight Python library for orchestrating and executing interdependent tasks. It supports automatic parallelism for independent tasks and ensures correct order for dependent ones.

Tasks can be:

- ✅ **Dependent** – tasks that rely on the result or side effects of others; they are executed **sequentially**.
- ⚡ **Independent** – tasks with no dependencies; they are executed **in parallel** to improve performance.


## 🚀 Features

- 🧩 Define tasks using plain Python functions or callables
- 🔗 Declare dependencies between tasks
- 🧠 Automatically builds a Directed Acyclic Graph (DAG)
- ⚙️ Executes tasks in correct dependency order
- ⚡ Parallel execution of independent tasks
- 📦 Shared context/result passing across tasks


## 🔧 Development

Using uv (Recommended):

```bash
uv sync
uv run main.py
```

or Using pip + virtual environment:

```bash
python3 -m venv .venv
sh .venv/Scripts/activate # or .venv/bin/activate on Windows
source .venv/Scripts/activate
pip install -e .
python main.py
```

## 🧠 Architecture (POC v1)

- Task Identification
  
    Mark plain Python functions as tasks using a class wrapper or (future) a decorator.

- Dependency Declaration

    Define simple upstream/downstream task relationships.

- DAG Construction

    Build an internal directed acyclic graph (DAG) where:
   - Nodes = tasks
   - Edges = dependencies

- Parallel & Sequential Execution

    Executes tasks in topological order:
    - Runs independent tasks concurrently
    - Respects dependency chains for serial execution

- Context Propagation

    Pass execution results and shared context from one task to its downstream dependencies.


## 🗺️ Roadmap (v2+ Ideas)

- [ ] Retry policy
- [ ] Timeout handling
- [ ] Tracking Task Lifecycle
- [ ] More intuitive task definition via `@task` decorator
- [ ] Support arbitrary callable signatures with dynamic args/kwargs resolution
- [ ] Async/await support
- [ ] Failure handling and rollback
- [ ] DAG visualization (`Graphviz`, `Networkx` or `Mermaid`)
- [ ] Support JSON-defined task flows 

    Allow users to define task graphs in a JSON/YAML format and load them dynamically.

    ```json
    {
    "tasks": [
        { "name": "fetch", "function": "my_module.fetch", "depends_on": [] },
        { "name": "process", "function": "my_module.process", "depends_on": ["fetch"] },
        { "name": "save", "function": "my_module.save", "depends_on": ["process"] }
    ]
    }
    ```