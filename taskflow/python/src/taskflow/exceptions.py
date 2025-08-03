class GraphCycleDetectedError(ValueError):
    """
    Custom exception raised when a cycle is detected in a graph where
    a topological sort is requested, indicating that the sort is not possible.
    """
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
