import sys
import os
from collections import defaultdict
from collections import deque

print(sys.path)
print(os.getenv("A"))

from taskflow.exceptions import GraphCycleDetectedError


class SimpleGraph[T]:
    """
    A basic directed graph implementation using adjacency lists.
    """

    def __init__(self) -> None:
        """
        Initializes an empty directed graph.
        """
        self._adj: dict[T, list[T]] = defaultdict(list)
        self._reverse_adj: dict[T, list[T]] = defaultdict(list)

    def add_vertex(self, vertex: T) -> None:
        """
        Adds a vertex to the graph if it doesn't already exist.
        """
        self._adj.setdefault(vertex, [])
        self._reverse_adj.setdefault(vertex, [])

    def add_edge(self, from_vertex: T, to_vertex: T) -> None:
        """
        Adds a directed edge from 'from_vertex' to 'to_vertex'.
        Automatically adds vertices if they don't exist.
        """
        self.add_vertex(from_vertex)
        self.add_vertex(to_vertex)

        if to_vertex not in self._adj[from_vertex]:
            self._adj[from_vertex].append(to_vertex)
            self._reverse_adj[to_vertex].append(from_vertex)

    def neighbors(self, vertex: T) -> list[T]:
        """
        Returns a list of vertices directly reachable from the given vertex (outgoing edges).
        Returns an empty list if the vertex is not in the graph or has no outgoing edges.
        """
        return self._adj.get(vertex, [])

    def successors(self, vertex: T) -> list[T]:
        """
        Alias for neighbors(), returns a list of vertices directly reachable from the given vertex.
        """
        return self.neighbors(vertex)

    def predecessors(self, vertex: T) -> list[T]:
        """
        Returns a list of vertices that have direct edges to the given vertex (incoming edges).
        Returns an empty list if the vertex is not in the graph or has no incoming edges.
        """
        return self._reverse_adj.get(vertex, [])

    def vertices(self) -> list[T]:
        """
        Returns a list of all unique vertices in the graph.
        The order is not guaranteed.
        """
        return list(self._adj.keys())

    def edges(self) -> list[tuple[T, T]]:
        """
        Returns a list of all directed edges in the graph as (from_vertex, to_vertex) tuples.
        """
        return [(f, t) for f in self._adj for t in self._adj[f]]

    def has_vertex(self, vertex: T) -> bool:
        """
        Checks if a given vertex exists in the graph.
        """
        return vertex in self._adj

    def has_edge(self, from_vertex: T, to_vertex: T) -> bool:
        """
        Checks if a directed edge exists from 'from_vertex' to 'to_vertex'.
        """
        return self.has_vertex(from_vertex) and to_vertex in self._adj[from_vertex]

    def topological_sort(self) -> list[T]:
        """
        Performs a topological sort on the graph.
        Returns a list of vertices in topological order.
        Raises ValueError if the graph contains a cycle.
        """
        # Kahn's algorithm
        # Important: Create a *copy* of in_degree to avoid modifying the graph's state
        # if the same graph instance is used for multiple topological_sort calls.
        # Also, ensure all vertices in _adj are accounted for in in_degree, even if their
        # initial in_degree is 0 and they are not keys in _reverse_adj (e.g., source nodes).
        in_degree = {v: len(pres) for v, pres in self._reverse_adj.items()}
        queue = deque([v for v in self._adj if in_degree[v] == 0])

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

        # If the number of processed vertices is less than the total number of vertices,
        # it means there's a cycle (or disconnected components that are part of a cycle).
        if visited_count != len(self._adj):
            raise GraphCycleDetectedError(
                "Graph contains a cycle, topological sort is not possible."
            )

        return order

    def has_cycle(self) -> bool:
        try:
            self.topological_sort()
        except GraphCycleDetectedError:
            return True
        return False

    def get_vertex_levels(self) -> dict[int, list[T]]:
        in_degree = {v: len(pres) for v, pres in self._reverse_adj.items()}
        queue = deque([v for v in self._adj if in_degree.get(v, 0) == 0])

        # BFS level traversal
        level = 0
        levels = defaultdict(list)
        while queue:
            for _ in range(len(queue)):
                vertex = queue.popleft()
                levels[level].append(vertex)
                for neighbor in self._adj[vertex]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
            level += 1

        return levels

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(vertices={self.vertices()}, edges={self.edges()})"


if __name__ == "__main__":
    graph: SimpleGraph[str] = SimpleGraph()
    graph.add_edge("taska", "taskc")
    graph.add_edge("taskb", "taskc")
    print(graph.vertices())
    print(graph.edges())
    print(graph.topological_sort())
