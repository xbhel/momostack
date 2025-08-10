class CycleDetectedException(Exception):
    """
    Custom exception raised when a cycle is detected in a graph where
    a topological sort is requested, indicating that the sort is not possible.
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class TaskException(Exception):
    """
    Base exception class.

    All Taskflow-specific exceptions should subclass this class.
    """

class TaskDefinitionException(TaskException):
    """
    Exception for task definition errors
    """
