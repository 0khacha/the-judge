"""Booking rules."""
from datetime import time

from .errors import RuleError

OPEN = time(8, 0)
CLOSE = time(18, 0)
OPEN_MINUTES = 600
MAX_MINUTES = 240
STEP = 15


def validate(start, end):
    if end <= start:
        raise RuleError("end must be after start")
    if start.date() != end.date():
        raise RuleError("a booking must stay within one day")
    for moment in (start, end):
        if moment.minute % STEP or moment.second or moment.microsecond:
            raise RuleError("times must be on a quarter hour")
    if start.time() < OPEN or end.time() > CLOSE:
        raise RuleError("outside opening hours")
    if (end - start).total_seconds() > MAX_MINUTES * 60:
        raise RuleError("a booking can last at most %d minutes" % MAX_MINUTES)
