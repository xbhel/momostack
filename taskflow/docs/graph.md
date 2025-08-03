# Graph

## Why does a graph contain a cycle, topological sort is not possible?

A topological sort is a linear ordering of vertices in a directed graph such that for every directed edge `u→v`, vertex `u` comes before vertex `v` in the ordering.

The key phrase here is "for every directed edge `u→v`, vertex `u` comes before vertex `v`."

Why this is impossible with a cycle:

Imagine a simple cycle: *A→B→C→A*.
1. If *A* comes before *B*: According to the edge A→B, this is fine.
2. If *B* comes before *C*: According to the edge *B→C*, this is also fine.
3. But what about *C→A*? For a topological sort to be valid, *C* must come before *A*.

This creates a contradiction:
1. *A* must be before *B*.
2. *B* must be before *C*.
3. *C* must be before *A*.

If *A* is before B, and *B* is before *C*, then logically *A* must be before *C*. But the edge *C→A* demands that *C* be before *A*. You can't have both!

*In essence, a cycle represents a circular dependency.* If task *A* depends on *B*, *B* depends on *C*, and *C* depends on *A*, then none of these tasks can ever be started or completed because they are all waiting on each other in an endless loop. *A* topological sort is precisely about finding a valid sequence to execute tasks with dependencies. If there's a circular dependency, no such valid sequence exists.

*Therefore, topological sorting is only possible on Directed Acyclic Graphs (DAGs).* The "Acyclic" part is crucial. If a directed graph contains a cycle, it is not a DAG, and a topological sort cannot be generated.

### Topological sorting Code Implementation

#### Recursion DFS Version

```python
def topological_sort(self) -> List[_T]:
    """
    Performs a topological sort on the graph.
    Returns a list of vertices in topological order.
    Raises ValueError if the graph contains a cycle.
    """
    if self.has_cycle():
        raise ValueError(
            "Graph contains a cycle, topological sort is not possible."
        )

    visited, order = set(), []

    def dfs(vertex):
        if vertex in visited:
            return
        visited.add(vertex)
        for neighbor in self.adj[vertex]:
            dfs(neighbor)
        order.append(vertex)

    for vertex in self._adj:
        dfs(vertex)
    return list(reversed(order))

def has_cycle(self) -> bool:
    visited, recursion_stack = set(), set()

    def dfs(vertex):
        if vertex in recursion_stack:
            return True
        if vertex in visited:
            return False

        visited.add(vertex)
        recursion_stack.add(vertex)
        for neighbor in self._adj[vertex]:
            if dfs(neighbor):
                return True
        recursion_stack.remove(vertex)
        return False

    return any(dfs(vertex) for vertex in self._adj)
```

#### FOR-Loop Version

```python
in_degree = {v: len(predecessors) for v, predecessors in self._reverse_adj.items()}
queue = deque([v for v in self._adj if in_degree.get(v, 0) == 0])

# Count of visited nodes to detect cycles
visited_count = 0
order = []
while queue:
    vertex = queue.popleft()
    order.append(vertex)
    visited_count += 1

    for neighbor in self._adj[vertex]:
        in_degree[neighbor] -= 1
        if in_degree[neighbor] == 0:
            queue.append(neighbor)

# If visited_count is not equal to the total number of vertices, a cycle exists
if visited_count != len(self._adj):
    raise ValueError(
        "Graph contains a cycle, topological sort is not possible."
    ) 

return order
```