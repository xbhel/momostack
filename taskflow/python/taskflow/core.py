from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Task:
    func: Callable[..., Any]
    name: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    description: Optional[str] = None
    status: str = field(default="created", init=False)
    result: Any = field(default=None, init=False)

    def __post__init__(self):
        self.name = self.name or self.func.__name__

    def run(self, ctx: Dict[str, Any]) -> Any:
        self.result = self.func(ctx)
        return self.result


class TaskExecutor:
    def __init__(self):
        self.tasks = {}
        self.task_graph = defaultdict(list)
        self.task_reversed_graph = defaultdict(list)

    def add_task(self, task: Task):
        task_name = task.name
        if task_name in self.tasks:
            raise ValueError(f"Task '{task_name}' already exists.")

        self.tasks[task_name] = task
        for x in task.depends_on:
            self.task_graph[x].append(task_name)
            self.task_reversed_graph[task_name].append(x)

    def run(self):
        context = {}
        completed_tasks = set()
        pending_tasks = set(self._topological_sort())

        with ThreadPoolExecutor() as pool:
            while pending_tasks:
                runnable_tasks = [
                    t
                    for t in pending_tasks
                    if all(d in completed_tasks for d in self.task_reversed_graph[t])
                ]
                futures = {
                    pool.submit(self.tasks[t].run, context): t for t in runnable_tasks
                }
                for future in as_completed(futures):
                    task_name = futures[future]
                    context[task_name] = future.result()
                    completed_tasks.add(task_name)
                    pending_tasks.remove(task_name)
            
        return context

    def _topological_sort(self):
        """
        Perform a topological sort on a DAG (Directed Acyclic Graph) of tasks:
        - nodes = tasks
        - edges = dependencies
        """
        visited, order = set(), []

        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            for neighbor in self.task_graph[node]:
                dfs(neighbor)
            order.append(node)

        for task in self.tasks:
            dfs(task)
        return list(reversed(order))


# A -> B -> C -> D
# A ————|
#       \
#        C -> D
#       /
# B ————|

def a(ctx):
    print(ctx)
    return 'a'

def b(ctx):
    print(ctx)
    return 'b'

def c(ctx):
    print(ctx)
    return 'c'

def d(ctx):
    print(ctx)
    return 'd'

task_executor = TaskExecutor()
task_executor.add_task(Task(a, name="a"))
task_executor.add_task(Task(b, name="b"))
task_executor.add_task(Task(c, name="c", depends_on=['a','b']))
task_executor.add_task(Task(d, name="d", depends_on=['c']))
task_executor.run()