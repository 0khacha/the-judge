"""Cron expression scheduler (standard library only)."""

import re
from datetime import datetime, timedelta

_SEARCH_DAYS = 3660

_MONTH_NAMES = {
    name: i
    for i, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}
_DOW_NAMES = {
    name: i
    for i, name in enumerate(["sun", "mon", "tue", "wed", "thu", "fri", "sat"])
}

# (name, low, high, names)
_FIELDS = (
    ("minute", 0, 59, None),
    ("hour", 0, 23, None),
    ("dom", 1, 31, None),
    ("month", 1, 12, _MONTH_NAMES),
    ("dow", 0, 7, _DOW_NAMES),
)

_ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

_DIGITS = re.compile(r"[0-9]+")
_NAME = re.compile(r"[A-Za-z]+")


def _value(token, low, high, names):
    if _DIGITS.fullmatch(token):
        value = int(token)
    elif names is not None and _NAME.fullmatch(token) and token.lower() in names:
        value = names[token.lower()]
    else:
        raise ValueError(f"invalid value {token!r}")
    if not low <= value <= high:
        raise ValueError(f"value {value} out of range {low}-{high}")
    return value


def _parse_item(item, low, high, names):
    base, slash, step_text = item.partition("/")
    if slash:
        if not _DIGITS.fullmatch(step_text):
            raise ValueError(f"invalid step in {item!r}")
        step = int(step_text)
        if step < 1:
            raise ValueError(f"step must be >= 1 in {item!r}")
    else:
        step = 1

    if base == "*":
        start, end = low, high
    else:
        parts = base.split("-")
        if len(parts) == 2:
            start = _value(parts[0], low, high, names)
            end = _value(parts[1], low, high, names)
            if start > end:
                raise ValueError(f"range start after end in {item!r}")
        elif len(parts) == 1:
            start = _value(parts[0], low, high, names)
            # "N/S" means N-max/S
            end = high if slash else start
        else:
            raise ValueError(f"malformed item {item!r}")
    return range(start, end + 1, step)


def _parse_field(text, low, high, names):
    values = set()
    for item in text.split(","):
        if item == "":
            raise ValueError(f"empty list item in {text!r}")
        values.update(_parse_item(item, low, high, names))
    return values


def _parse(expr):
    if not isinstance(expr, str):
        raise TypeError("cron expression must be a string")
    text = expr.strip()
    if text.startswith("@"):
        if text not in _ALIASES:
            raise ValueError(f"unknown alias {text!r}")
        text = _ALIASES[text]

    raw_fields = text.split()
    if len(raw_fields) != 5:
        raise ValueError(f"expected 5 fields, got {len(raw_fields)}")

    sets = {}
    restricted = {}
    for raw, (name, low, high, names) in zip(raw_fields, _FIELDS):
        values = _parse_field(raw, low, high, names)
        if name == "dow":
            values = {v % 7 for v in values}  # 7 means Sunday
        sets[name] = values
        restricted[name] = not raw.startswith("*")
    return sets, restricted


def _check_after(after):
    if not isinstance(after, datetime):
        raise TypeError("'after' must be a datetime.datetime")
    if after.tzinfo is not None:
        raise ValueError("'after' must be a naive datetime")


def _day_matches(sets, restricted, day):
    if day.month not in sets["month"]:
        return False
    dom_ok = day.day in sets["dom"]
    dow_ok = ((day.weekday() + 1) % 7) in sets["dow"]  # Sunday = 0
    if restricted["dom"] and restricted["dow"]:
        return dom_ok or dow_ok
    return dom_ok and dow_ok


def _search(sets, restricted, start, limit):
    t = start
    while t <= limit:
        if t.month not in sets["month"]:
            if t.month == 12:
                t = datetime(t.year + 1, 1, 1)
            else:
                t = datetime(t.year, t.month + 1, 1)
            continue
        if not _day_matches(sets, restricted, t):
            t = t.replace(hour=0, minute=0) + timedelta(days=1)
            continue
        if t.hour not in sets["hour"]:
            t = t.replace(minute=0) + timedelta(hours=1)
            continue
        if t.minute not in sets["minute"]:
            t = t + timedelta(minutes=1)
            continue
        return t
    return None


def _next(sets, restricted, after):
    start = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    try:
        limit = after + timedelta(days=_SEARCH_DAYS)
    except OverflowError:
        limit = datetime.max
    try:
        found = _search(sets, restricted, start, limit)
    except OverflowError:
        found = None
    if found is None:
        raise ValueError(f"no matching time within {_SEARCH_DAYS} days")
    return found


def next_run(expr, after):
    """Return the earliest datetime strictly after `after` matching `expr`."""
    _check_after(after)
    sets, restricted = _parse(expr)
    return _next(sets, restricted, after)


def next_runs(expr, after, count):
    """Return the next `count` datetimes matching `expr`, each after the previous."""
    _check_after(after)
    sets, restricted = _parse(expr)
    if not isinstance(count, int):
        raise TypeError("count must be an int")
    if count < 0:
        raise ValueError("count must be >= 0")
    results = []
    current = after
    for _ in range(count):
        current = _next(sets, restricted, current)
        results.append(current)
    return results
