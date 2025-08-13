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

# prod
uv sync --no-dev
```

or Using pip + virtual environment:

```bash
python3 -m venv .venv
sh .venv/Scripts/activate # or .venv/bin/activate on Windows
source .venv/Scripts/activate
pip install -e .
python main.py
pip install ".[dev]"
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

## Useful links

- [networkx](https://networkx.org/documentation/latest/tutorial.html)
- [graph](https://www.geeksforgeeks.org/python/graphs-in-python-1/)
- [mermaid](https://mermaid.js.org/syntax/gitgraph.html)

### General-purpose graph data structures 

| Library                                                                  | Description                                                                  | Pros                                                                     | Best For                                                           | Visualization Support                                        | License    |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------ | ---------- |
| [**NetworkX**](https://networkx.org/)                                    | Pure Python library for creating, manipulating, and studying graphs.         | Very popular and well-documented; rich algorithm support; easy to learn. | Small to medium-sized graph analysis, teaching, quick prototyping. | Basic drawing via Matplotlib; integrates with PyGraphviz     | BSD        |
| [**igraph (python-igraph)**](https://igraph.org/python/)                 | High-performance graph analysis library with a C core and Python bindings.   | Fast, handles large graphs; rich set of algorithms.                      | Large-scale network analysis where speed is important.             | Built-in plotting (Matplotlib, Cairo)                        | GPL-2      |
| [**graph-tool**](https://graph-tool.skewed.de/)                          | C++/Boost-based graph library with Python interface for extreme performance. | Extremely fast; supports parallel algorithms.                            | Very large graphs and high-performance computing.                  | Built-in high-quality visualizations                         | GPL-3      |
| [**retworkx**](https://github.com/Qiskit/retworkx)                       | Rust-powered graph library with a NetworkX-like API.                         | Very fast; safer memory handling; easy transition from NetworkX.         | Performance-sensitive graph algorithms.                            | No built-in, can export to Graphviz/NetworkX for plotting    | Apache-2.0 |
| [**networkit**](https://networkit.github.io/)                            | C++ backend for high-performance network analysis.                           | Scales to massive graphs; modern algorithm implementations.              | Analyzing huge networks efficiently.                               | Minimal, exports to external visualization tools             | MIT        |
| [**pygraphviz**](https://pygraphviz.github.io/)                          | Python interface to Graphviz for graph layout and visualization.             | Excellent layouts; integrates with NetworkX; easy rendering.             | Visualizing graphs with professional layouts.                      | Yes, via Graphviz                                            | BSD        |
| [**PyTorch Geometric (PyG)**](https://pytorch-geometric.readthedocs.io/) | PyTorch-based library for Graph Neural Networks.                             | Large model zoo; well-maintained; integrates with PyTorch.               | Machine learning and deep learning on graphs.                      | No built-in; relies on external tools (Matplotlib, NetworkX) | MIT        |
| [**Deep Graph Library (DGL)**](https://www.dgl.ai/)                      | Multi-framework GNN library supporting PyTorch, MXNet, TensorFlow.           | Flexible; supports heterogeneous graphs.                                 | Research & production GNNs with multi-framework support.           | No built-in; external tools required                         | Apache-2.0 |
| [**Spektral**](https://graphneural.network/)                             | Graph Neural Networks in TensorFlow/Keras.                                   | Simple, Keras-friendly API; good for experimentation.                    | TF/Keras-based GNN modeling.                                       | No built-in; relies on NetworkX/Matplotlib                   | MIT        |
