"""Serialisation of a TaskStore to plain dicts (JSON compatible)."""
from datetime import date

from .models import Task
from .store import TaskStore


def _d(value):
    return value.isoformat() if value else None


def _p(value):
    return date.fromisoformat(value) if value else None


def task_to_dict(task):
    return {
        "id": task.id, "title": task.title, "due": _d(task.due), "priority": task.priority,
        "tags": list(task.tags), "deps": list(task.deps), "status": task.status,
        "done_on": _d(task.done_on), "repeat": task.repeat, "next_id": task.next_id,
    }


def task_from_dict(data):
    return Task(
        id=data["id"], title=data["title"], due=_p(data.get("due")),
        priority=data.get("priority", 2), tags=list(data.get("tags", [])),
        deps=list(data.get("deps", [])), status=data.get("status", "open"),
        done_on=_p(data.get("done_on")), repeat=data.get("repeat"), next_id=data.get("next_id"),
    )


def dump(store):
    return {"next_id": store._next_id, "tasks": [task_to_dict(t) for t in store.tasks()]}


def load(data, clock=None):
    store = TaskStore(clock)
    for item in data.get("tasks", []):
        task = task_from_dict(item)
        store._tasks[task.id] = task
    store._next_id = data.get("next_id", max(store._tasks, default=0) + 1)
    return store
