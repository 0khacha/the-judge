"""Text views."""
from datetime import timedelta


def task_line(task):
    return "#%d [P%d] %s" % (task.id, task.priority, task.title)


def agenda(store, days=7):
    """Open tasks due within `days` days from today (overdue ones first, flagged OVERDUE)."""
    today = store.today()
    horizon = today + timedelta(days=days)
    lines = ["Agenda for %s (next %d days)" % (today.isoformat(), days)]
    shown = [t for t in store.tasks("open") if t.due is not None and t.due <= horizon]
    for task in shown:
        text = "  %s (due %s)" % (task_line(task), task.due.isoformat())
        if task.repeat is not None:
            text += " (repeats %s)" % task.repeat
        if task.due < today:
            text += " OVERDUE"
        lines.append(text)
    if not shown:
        lines.append("  nothing due")
    return "\n".join(lines)


def summary(store):
    return "open: %d, done: %d, overdue: %d" % (
        len(store.tasks("open")), len(store.tasks("done")), len(store.overdue()))
