"""Next occurrence of a recurring task."""
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
