"""The task store."""
import calendar
from datetime import date, timedelta

from .models import Task

REPEAT_KINDS = ("daily", "weekly", "monthly")


class BlockedError(Exception):
    """A dependency of the task is not done yet."""


def next_due(due, repeat):
    """Due date of the next occurrence of a recurring task."""
    if repeat == "daily":
        return due + timedelta(days=1)
    if repeat == "weekly":
        return due + timedelta(days=7)
    if repeat == "monthly":
        index = due.year * 12 + (due.month - 1) + 1
        year, month = divmod(index, 12)
        month += 1
        return date(year, month, min(due.day, calendar.monthrange(year, month)[1]))
    raise ValueError("unknown repeat %r" % (repeat,))


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
        deps = sorted(set(deps))
        for dep in deps:
            if dep not in self._tasks:
                raise ValueError("unknown dependency %s" % dep)
        if repeat is not None and repeat not in REPEAT_KINDS:
            raise ValueError("repeat must be daily, weekly or monthly")
        if repeat is not None and due is None:
            raise ValueError("a recurring task needs a due date")
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
        following = next_due(task.due, task.repeat) if task.repeat else None
        task.status = "done"
        task.done_on = self.today()
        if following is not None:
            nxt = self.add(task.title, due=following, priority=task.priority,
                           tags=list(task.tags), repeat=task.repeat)
            task.next_id = nxt.id
        return task

    def reopen(self, task_id):
        task = self.get(task_id)
        if task.is_open:
            raise ValueError("task %d is not done" % task_id)
        successor = self._tasks.get(task.next_id) if task.next_id is not None else None
        if successor is not None and successor.is_open:
            raise ValueError("task %d has open successor %d" % (task_id, task.next_id))
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
