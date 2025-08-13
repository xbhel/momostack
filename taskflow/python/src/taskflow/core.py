from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Any

from .exceptions import TaskDefinitionException
from .graph import SimpleGraph


@unique
class TaskStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    RUNNING = "running"


@dataclass
class Task:
    func: Callable[..., Any]
    name: str | None = None
    depends_on: list[str] = field(default_factory=list)
    description: str | None = None
    status: TaskStatus = field(default=TaskStatus.CREATED, init=False)
    result: Any = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.name = self.name or self.func.__name__

    def run(self, ctx: dict[str, Any]) -> Any:
        self.status = TaskStatus.RUNNING
        self.result = self.func(ctx)
        return self.result


class TaskExecutor:
    def __init__(self) -> None:
        self.tasks: dict[str, Task] = {}
        self.task_graph: SimpleGraph[str] = SimpleGraph()

    def add_task(self, task: Task) -> None:
        task_name = task.name
        if task_name is None:
            raise TaskDefinitionException("Task name cannot be empty")

        if task_name in self.tasks:
            raise TaskDefinitionException(f"Task '{task_name}' already exists.")

        self.tasks[task_name] = task
        self.task_graph.add_vertex(task_name)

        for pre_task in task.depends_on:
            self.task_graph.add_edge(pre_task, task_name)

    def run(self) -> dict[str, Any]:
        self._check_task_definitions()

        context: dict[str, Any] = {}
        completed: set[str] = set()
        pending = set(self.task_graph.topological_sort())

        with ThreadPoolExecutor(thread_name_prefix="taskflow-") as pool:
            while pending:
                runnable_tasks = [
                    t
                    for t in pending
                    if all(pre in completed for pre in self.task_graph.predecessors(t))
                ]

                futures: dict[Future[Any], str] = {}
                for task_name in runnable_tasks:
                    task = self.tasks[task_name]
                    task.status = TaskStatus.QUEUED
                    future = pool.submit(task.run, {**context})
                    futures[future] = task_name

                for future in as_completed(futures):
                    task_name = futures[future]
                    try:
                        context[task_name] = future.result()
                        self.tasks[task_name].status = TaskStatus.COMPLETED
                    except Exception:
                        self.tasks[task_name].status = TaskStatus.FAILED
                        # add a flag to enable fast-fail or not
                        raise

                    completed.add(task_name)
                    pending.remove(task_name)

        return context

    def _check_task_definitions(self) -> None:
        undefined_tasks = set(self.task_graph.vertices()) - set(self.tasks.keys())
        if undefined_tasks:
            tasks = ','.join(sorted(undefined_tasks))
            raise TaskDefinitionException(f"Undefined task(s) detected: '{tasks}'")

        if self.task_graph.has_cycle():
            raise TaskDefinitionException(
                "A cycle was detected in the task dependency graph. "
                "Check for circular dependencies and remove them."
            )

    def _on_task_failure(self, task: Task) -> None:
        pass

    def _on_task_completed(self, task: Task) -> None:
        pass

    def _on_task_retry(self, task: Task) -> None:
        pass


def a(ctx: dict[str, Any]) -> str:
    print(ctx)
    return "a"


def b(ctx: dict[str, Any]) -> str:
    print(ctx)
    return "b"


def c(ctx: dict[str, Any]) -> str:
    print(ctx)
    return "c"


def d(ctx: dict[str, Any]) -> str:
    print(ctx)
    return "d"


task_executor = TaskExecutor()
task_executor.add_task(Task(a, name="a"))
task_executor.add_task(Task(b, name="b"))
task_executor.add_task(Task(c, name="c", depends_on=["a", "b"]))
task_executor.add_task(Task(d, name="d", depends_on=["c"]))
result = task_executor.run()
print(result)
print(task_executor.tasks)
