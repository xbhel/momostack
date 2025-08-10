from collections import deque
from typing import Generic, TypeVar

from .exceptions import CycleDetectedException

T = TypeVar("T")


class SimpleGraph(Generic[T]):
    """
    A basic directed graph implementation using adjacency lists.
    """

    def __init__(self) -> None:
        """
        Initializes an empty directed graph.
        """
        self._adj: dict[T, list[T]] = {}
        self._reverse_adj: dict[T, list[T]] = {}

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
        Returns a list of vertices directly reachable from the given vertex
        (outgoing edges).

        Returns an empty list if the vertex is not in the graph or has no
        outgoing edges.
        """
        return self._adj.get(vertex, [])

    def successors(self, vertex: T) -> list[T]:
        """
        Alias for neighbors(), returns a list of vertices directly reachable from
        the given vertex.
        """
        return self.neighbors(vertex)

    def predecessors(self, vertex: T) -> list[T]:
        """
        Returns a list of vertices that have direct edges to the given vertex
        (incoming edges).
        Returns an empty list if the vertex is not in the graph or has no
        incoming edges.
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
        Returns a list of all directed edges in the graph as (from_vertex, to_vertex)
         tuples.
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
        # Also, ensure all vertices in _adj are accounted for in in_degree,
        # even if their initial in_degree is 0 and they are not keys in _reverse_adj
        # (e.g., source nodes).
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
        # it means there's a cycle (or disconnected components that are part of a cycle)
        if visited_count != len(self._adj):
            raise CycleDetectedException(
                "Graph contains a cycle, topological sort is not possible."
            )

        return order

    def has_cycle(self) -> bool:
        visited: set[T] = set()
        recursion_stack: set[T] = set()

        def dfs(vertex: T) -> bool:
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

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f"{cls_name}(vertices={self.vertices()}, edges={self.edges()})"
