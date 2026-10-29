from datetime import datetime, timedelta

_ALIASES = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}
_MONTHS = {n: i + 1 for i, n in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_DOWS = {n: i for i, n in enumerate(["sun", "mon", "tue", "wed", "thu", "fri", "sat"])}


def _value(tok, lo, hi, names):
    if tok.isascii() and tok.isdigit():
        v = int(tok)
    elif names and tok.lower() in names:
        v = names[tok.lower()]
    else:
        raise ValueError("bad value %r" % tok)
    if v < lo or v > hi:
        raise ValueError("value out of range: %r" % tok)
    return v


def _parse_field(text, lo, hi, names=None):
    """Return (set_of_values, restricted)."""
    values = set()
    for item in text.split(","):
        if item == "":
            raise ValueError("empty item")
        step = None
        base = item
        if "/" in item:
            base, _, s = item.partition("/")
            if not (s.isascii() and s.isdigit()) or int(s) < 1:
                raise ValueError("bad step %r" % s)
            step = int(s)
        if base == "*":
            a, b = lo, hi
        elif "-" in base:
            x, _, y = base.partition("-")
            a, b = _value(x, lo, hi, names), _value(y, lo, hi, names)
            if a > b:
                raise ValueError("reversed range")
        else:
            a = _value(base, lo, hi, names)
            b = hi if step is not None else a
        values.update(range(a, b + 1, step or 1))
    return values, not text.startswith("*")


def _compile(expr):
    if not isinstance(expr, str):
        raise TypeError("expr must be a str")
    expr = expr.strip()
    if expr.startswith("@"):
        if expr not in _ALIASES:
            raise ValueError("unknown alias")
        expr = _ALIASES[expr]
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError("expected 5 fields")
    minutes, _ = _parse_field(parts[0], 0, 59)
    hours, _ = _parse_field(parts[1], 0, 23)
    doms, dom_r = _parse_field(parts[2], 1, 31)
    months, _ = _parse_field(parts[3], 1, 12, _MONTHS)
    dows, dow_r = _parse_field(parts[4], 0, 7, _DOWS)
    if 7 in dows:
        dows.add(0)
        dows.discard(7)
    return sorted(minutes), sorted(hours), doms, dom_r, months, dows, dow_r


def _day_ok(c, day):
    _, _, doms, dom_r, months, dows, dow_r = c
    if day.month not in months:
        return False
    dom_ok = day.day in doms
    dow_ok = day.isoweekday() in dows
    if dom_r and dow_r:
        return dom_ok or dow_ok
    return dom_ok and dow_ok


def _next(c, after):
    start = after.replace(second=0, microsecond=0)
    if after.second == 0 and after.microsecond == 0:
        start += timedelta(minutes=1)
    first = start.date()
    for k in range(3661):
        day = first + timedelta(days=k)
        if not _day_ok(c, day):
            continue
        for h in c[1]:
            for m in c[0]:
                cand = datetime(day.year, day.month, day.day, h, m)
                if cand >= start:
                    return cand
    raise ValueError("no matching time within 3660 days")


def _check_after(after):
    if not isinstance(after, datetime):
        raise TypeError("after must be a datetime")
    if after.tzinfo is not None:
        raise ValueError("after must be naive")


def next_run(expr, after):
    c = _compile(expr)
    _check_after(after)
    return _next(c, after)


def next_runs(expr, after, count):
    c = _compile(expr)
    _check_after(after)
    if isinstance(count, bool) or not isinstance(count, int):
        raise TypeError("count must be an int")
    if count < 0:
        raise ValueError("count must be >= 0")
    out = []
    cur = after
    for _ in range(count):
        cur = _next(c, cur)
        out.append(cur)
    return out
