"""The task store."""
from datetime import date

from .models import Task
from .recur import KINDS, next_due


class BlockedError(Exception):
    """A dependency of the task is not done yet."""


class TaskStore:
    def __init__(self, clock=None):
        self.clock = clock or date.today
        self._tasks = {}
        self._next_id = 1

    def today(self):
        return self.clock()

    def add(self, title, due=None, priority=2, tags=(), deps=(), repeat=None):
        title = (title or "").strip()
        if not title:
            raise ValueError("title required")
        if priority not in (1, 2, 3):
            raise ValueError("priority must be 1, 2 or 3")
        if repeat is not None:
            if repeat not in KINDS:
                raise ValueError("unknown repeat %r" % (repeat,))
            if due is None:
                raise ValueError("a recurring task needs a due date")
        deps = sorted(set(deps))
        for dep in deps:
            if dep not in self._tasks:
                raise ValueError("unknown dependency %s" % dep)
        task = Task(self._next_id, title, due, priority, sorted(set(tags)), deps, repeat=repeat)
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def get(self, task_id):
        if task_id not in self._tasks:
            raise KeyError(task_id)
        return self._tasks[task_id]

    def complete(self, task_id):
        """Mark a task done (today). Returns the task."""
        task = self.get(task_id)
        if not task.is_open:
            raise ValueError("task %d is already done" % task_id)
        for dep in task.deps:
            if self._tasks[dep].is_open:
                raise BlockedError("task %d waits for %d" % (task_id, dep))
        task.status = "done"
        task.done_on = self.today()
        if task.repeat:
            nxt = self.add(task.title, next_due(task.due, task.repeat), task.priority,
                           list(task.tags), (), task.repeat)
            task.next_id = nxt.id
        return task

    def reopen(self, task_id):
        task = self.get(task_id)
        if task.is_open:
            raise ValueError("task %d is not done" % task_id)
        succ = self._tasks.get(task.next_id) if task.next_id is not None else None
        if succ is not None and succ.is_open:
            raise ValueError("task %d already has an open next occurrence" % task_id)
        task.status = "open"
        task.done_on = None
        task.next_id = None
        return task

    def delete(self, task_id):
        self.get(task_id)
        for other in self._tasks.values():
            if other.is_open and task_id in other.deps:
                raise ValueError("task %d is needed by open task %d" % (task_id, other.id))
        del self._tasks[task_id]
        for other in self._tasks.values():
            if task_id in other.deps:
                other.deps.remove(task_id)
            if other.next_id == task_id:
                other.next_id = None

    def tasks(self, status=None, tag=None):
        """Tasks ordered by due date (no date last), then higher priority first, then id."""
        found = [t for t in self._tasks.values()
                 if (status is None or t.status == status) and (tag is None or tag in t.tags)]
        return sorted(found, key=lambda t: (t.due is None, t.due or date.max, -t.priority, t.id))

    def ready(self):
        """Open tasks whose dependencies are all done."""
        return [t for t in self.tasks("open") if all(not self._tasks[d].is_open for d in t.deps)]

    def overdue(self):
        today = self.today()
        return [t for t in self.tasks("open") if t.due is not None and t.due < today]
