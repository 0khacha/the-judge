import os, json
from _h import *
T = "D3_tracker"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
rep(p("tracker/models.py"), "    done_on: Optional[date] = None\n", "    done_on: Optional[date] = None\n    repeat: Optional[str] = None\n    next_id: Optional[int] = None\n")
open(p("tracker/recur.py"), "w").write('''"""Next occurrence of a recurring task."""
import calendar
from datetime import timedelta

KINDS = ("daily", "weekly", "monthly")


def next_due(due, kind):
    if kind == "daily":
        return due + timedelta(days=1)
    if kind == "weekly":
        return due + timedelta(days=7)
    if kind == "monthly":
        year, month = (due.year + 1, 1) if due.month == 12 else (due.year, due.month + 1)
        last = calendar.monthrange(year, month)[1]
        return due.replace(year=year, month=month, day=min(due.day, last))
    raise ValueError("unknown repeat %r" % (kind,))
''')
s = p("tracker/store.py")
rep(s, "from .models import Task\n", "from .models import Task\nfrom .recur import KINDS, next_due\n")
rep(s, "def add(self, title, due=None, priority=2, tags=(), deps=()):", "def add(self, title, due=None, priority=2, tags=(), deps=(), repeat=None):")
rep(s, "        deps = sorted(set(deps))\n", "        if repeat is not None:\n            if repeat not in KINDS:\n                raise ValueError(\"unknown repeat %r\" % (repeat,))\n            if due is None:\n                raise ValueError(\"a recurring task needs a due date\")\n        deps = sorted(set(deps))\n")
rep(s, "Task(self._next_id, title, due, priority, sorted(set(tags)), deps)", "Task(self._next_id, title, due, priority, sorted(set(tags)), deps, repeat=repeat)")
rep(s, "        task.done_on = self.today()\n        return task\n", "        task.done_on = self.today()\n        if task.repeat:\n            nxt = self.add(task.title, next_due(task.due, task.repeat), task.priority,\n                           list(task.tags), (), task.repeat)\n            task.next_id = nxt.id\n        return task\n")
rep(s, "            raise ValueError(\"task %d is not done\" % task_id)\n        task.status = \"open\"\n        task.done_on = None\n", "            raise ValueError(\"task %d is not done\" % task_id)\n        succ = self._tasks.get(task.next_id) if task.next_id is not None else None\n        if succ is not None and succ.is_open:\n            raise ValueError(\"task %d already has an open next occurrence\" % task_id)\n        task.status = \"open\"\n        task.done_on = None\n        task.next_id = None\n")
rep(s, "            if task_id in other.deps:\n                other.deps.remove(task_id)\n", "            if task_id in other.deps:\n                other.deps.remove(task_id)\n            if other.next_id == task_id:\n                other.next_id = None\n")
g = p("tracker/storage.py")
rep(g, '        "done_on": _d(task.done_on),\n', '        "done_on": _d(task.done_on), "repeat": task.repeat, "next_id": task.next_id,\n')
rep(g, '        done_on=_p(data.get("done_on")),\n', '        done_on=_p(data.get("done_on")), repeat=data.get("repeat"), next_id=data.get("next_id"),\n')
v = p("tracker/views.py")
rep(v, '        if task.due < today:', '        if task.repeat:\n            text += " (repeats %s)" % task.repeat\n        if task.due < today:')
c = p("tracker/cli.py")
rep(c, "tags=opt.get(\"--tag\", []), deps=[int(d) for d in opt.get(\"--dep\", [])])", "tags=opt.get(\"--tag\", []), deps=[int(d) for d in opt.get(\"--dep\", [])],\n                     repeat=opt.get(\"--repeat\"))")
rep(c, '    out("done #%d" % task.id)', '    out("done #%d" % task.id)\n    if task.next_id is not None:\n        nxt = store.get(task.next_id)\n        out("next #%d due %s" % (nxt.id, nxt.due.isoformat()))')
rep(c, '    return "#%d [%s] P%d %s due %s" % (\n        task.id, task.status, task.priority, task.title, task.due.isoformat() if task.due else "-")', '    text = "#%d [%s] P%d %s due %s" % (\n        task.id, task.status, task.priority, task.title, task.due.isoformat() if task.due else "-")\n    if task.repeat:\n        text += " repeat %s" % task.repeat\n    return text')
rep(c, "[--dep ID]\")", "[--dep ID] [--repeat KIND]\")")

w = clone(T, "reference", "wrong_1")   # no persistence, no next_id cleanup on delete, no cli/agenda marks
rep(os.path.join(w, "tracker/storage.py"), '"repeat": task.repeat, "next_id": task.next_id,\n', '\n')
rep(os.path.join(w, "tracker/storage.py"), 'repeat=data.get("repeat"), next_id=data.get("next_id"),\n', '\n')
rep(os.path.join(w, "tracker/store.py"), "            if other.next_id == task_id:\n                other.next_id = None\n", "")
w = clone(T, "reference", "wrong_2")   # delete no longer detaches the deleted task from other tasks' deps
rep(os.path.join(w, "tracker/store.py"), "            if task_id in other.deps:\n                other.deps.remove(task_id)\n", "")
json.dump({"task": T, "lines": 0, "change_requirements": 8, "traps": [
 "due computed from old due, monthly clamp / year rollover",
 "storage must persist repeat and next_id and load old data",
 "delete must reset predecessor next_id",
 "reopen with open successor rejected, resets next_id",
 "failed completion must not spawn; rejected add consumes no id",
 "agenda suffix order before OVERDUE; cli done second line; list suffix",
 "regression: delete detaches done dep from other tasks' deps, ordering, ready"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
