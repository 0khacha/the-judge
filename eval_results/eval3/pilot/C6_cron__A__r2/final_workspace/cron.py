"""Cron expression scheduler. Standard library only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta

__all__ = ["next_run", "next_runs"]

_MAX_SEARCH_DAYS = 3660
_DIGITS = re.compile(r"[0-9]+")
_NAME = re.compile(r"[A-Za-z]{3}")

_ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

_MONTH_NAMES = {
    name: index
    for index, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}
_DOW_NAMES = {
    name: index
    for index, name in enumerate(["sun", "mon", "tue", "wed", "thu", "fri", "sat"])
}


@dataclass(frozen=True)
class _Field:
    name: str
    lo: int
    hi: int
    names: dict | None


_FIELDS = (
    _Field("minute", 0, 59, None),
    _Field("hour", 0, 23, None),
    _Field("day-of-month", 1, 31, None),
    _Field("month", 1, 12, _MONTH_NAMES),
    _Field("day-of-week", 0, 7, _DOW_NAMES),
)


@dataclass(frozen=True)
class _Spec:
    minutes: tuple
    hours: tuple
    doms: frozenset
    months: frozenset
    dows: frozenset
    dom_restricted: bool
    dow_restricted: bool


def _parse_value(token: str, fld: _Field) -> int:
    if _DIGITS.fullmatch(token):
        value = int(token)
        if value < fld.lo or value > fld.hi:
            raise ValueError(f"{fld.name} value out of range: {token!r}")
        return value
    if fld.names is not None and _NAME.fullmatch(token):
        key = token.lower()
        if key in fld.names:
            return fld.names[key]
    raise ValueError(f"invalid {fld.name} value: {token!r}")


def _parse_field(text: str, fld: _Field) -> frozenset:
    values: set[int] = set()
    for item in text.split(","):
        if item == "":
            raise ValueError(f"empty item in {fld.name} field")
        parts = item.split("/")
        if len(parts) > 2:
            raise ValueError(f"malformed item in {fld.name} field: {item!r}")
        base = parts[0]
        step = None
        if len(parts) == 2:
            if not _DIGITS.fullmatch(parts[1]):
                raise ValueError(f"invalid step in {fld.name} field: {item!r}")
            step = int(parts[1])
            if step < 1:
                raise ValueError(f"step must be >= 1 in {fld.name} field: {item!r}")
        if base == "*":
            start, end = fld.lo, fld.hi
        elif "-" in base:
            pieces = base.split("-")
            if len(pieces) != 2:
                raise ValueError(f"malformed range in {fld.name} field: {item!r}")
            start = _parse_value(pieces[0], fld)
            end = _parse_value(pieces[1], fld)
            if start > end:
                raise ValueError(f"range start after end in {fld.name} field: {item!r}")
        else:
            start = _parse_value(base, fld)
            end = fld.hi if step is not None else start
        values.update(range(start, end + 1, step or 1))
    return frozenset(values)


def _parse(expr) -> _Spec:
    if not isinstance(expr, str):
        raise TypeError("cron expression must be a str")
    text = expr.strip()
    if text.startswith("@"):
        if text not in _ALIASES:
            raise ValueError(f"unknown cron alias: {text!r}")
        text = _ALIASES[text]
    tokens = text.split()
    if len(tokens) != 5:
        raise ValueError(f"cron expression must have 5 fields, got {len(tokens)}")

    minutes, hours, doms, months, dows = (
        _parse_field(tok, fld) for tok, fld in zip(tokens, _FIELDS)
    )
    # Sunday is 0 and 7 both; normalise 7 to 0.
    dows = frozenset(v % 7 for v in dows)
    return _Spec(
        minutes=tuple(sorted(minutes)),
        hours=tuple(sorted(hours)),
        doms=doms,
        months=months,
        dows=dows,
        dom_restricted=not tokens[2].startswith("*"),
        dow_restricted=not tokens[4].startswith("*"),
    )


def _check_after(after) -> None:
    if not isinstance(after, datetime):
        raise TypeError("'after' must be a datetime.datetime")
    if after.tzinfo is not None:
        raise ValueError("'after' must be a naive datetime (tzinfo None)")


def _day_matches(spec: _Spec, day) -> bool:
    if day.month not in spec.months:
        return False
    dom_ok = day.day in spec.doms
    dow_ok = (day.weekday() + 1) % 7 in spec.dows  # Python Monday=0 -> cron Monday=1
    if spec.dom_restricted and spec.dow_restricted:
        return dom_ok or dow_ok
    return dom_ok and dow_ok


def _search(spec: _Spec, after: datetime) -> datetime | None:
    try:
        start = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    except OverflowError:
        return None
    try:
        limit = after + timedelta(days=_MAX_SEARCH_DAYS)
    except OverflowError:
        limit = datetime.max

    day = start.date()
    last = limit.date()
    while True:
        if _day_matches(spec, day):
            for hour in spec.hours:
                for minute in spec.minutes:
                    candidate = datetime.combine(day, time(hour, minute))
                    if candidate < start:
                        continue
                    if candidate > limit:
                        return None
                    return candidate
        if day >= last:
            return None
        day += timedelta(days=1)


def _next(spec: _Spec, after: datetime) -> datetime:
    result = _search(spec, after)
    if result is None:
        raise ValueError("cron expression has no match within 3660 days")
    return result


def next_run(expr: str, after: datetime) -> datetime:
    """Return the earliest datetime strictly after ``after`` matching ``expr``."""
    spec = _parse(expr)
    _check_after(after)
    return _next(spec, after)


def next_runs(expr: str, after: datetime, count: int) -> list[datetime]:
    """Return the next ``count`` matches of ``expr`` strictly after ``after``."""
    spec = _parse(expr)
    _check_after(after)
    if not isinstance(count, int) or isinstance(count, bool):
        raise TypeError("'count' must be an int")
    if count < 0:
        raise ValueError("'count' must be >= 0")
    results: list[datetime] = []
    current = after
    for _ in range(count):
        current = _next(spec, current)
        results.append(current)
    return results
