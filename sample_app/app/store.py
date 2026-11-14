"""In-memory storage for tasks.

Tests rely on two things staying stable:
  * `app.main.app` is the FastAPI application
  * `app.store.reset()` clears all data
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import Task, TaskCreate

_tasks: Dict[int, Task] = {}
_next_id = 1


def reset() -> None:
    global _next_id
    _tasks.clear()
    _next_id = 1


def create(data: TaskCreate) -> Task:
    global _next_id
    task = Task(
        id=_next_id,
        title=data.title,
        description=data.description,
        created_at=datetime.now(timezone.utc),
    )
    _tasks[task.id] = task
    _next_id += 1
    return task


def list_all() -> List[Task]:
    return list(_tasks.values())


def get(task_id: int) -> Optional[Task]:
    return _tasks.get(task_id)


def save(task: Task) -> Task:
    _tasks[task.id] = task
    return task


def delete(task_id: int) -> bool:
    return _tasks.pop(task_id, None) is not None
