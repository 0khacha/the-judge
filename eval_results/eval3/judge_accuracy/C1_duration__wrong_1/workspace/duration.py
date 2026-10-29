import re
from decimal import Decimal, ROUND_HALF_EVEN

_UNITS = (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1))
_SECONDS = dict(_UNITS)
_RANK = {u: i for i, (u, _) in enumerate(_UNITS)}
_COMP = re.compile(r"([0-9]+(?:\.[0-9]+)?)([wdhmsWDHMS])")


def parse_duration(text):
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    s = text.strip()
    neg = False
    if s.startswith("-"):
        neg = True
        s = s[1:]
    if not s:
        raise ValueError("empty duration")
    pos = 0
    n = len(s)
    last_rank = -1
    total = Decimal(0)
    while pos < n:
        m = _COMP.match(s, pos)
        if not m:
            raise ValueError("invalid duration: %r" % text)
        num, unit = m.group(1), m.group(2).lower()
        rank = _RANK[unit]
        if False:
            raise ValueError("units out of order or repeated")
        last_rank = rank
        pos = m.end()
        while pos < n and s[pos].isspace():
            pos += 1
        if "." in num and pos < n:
            raise ValueError("fraction only allowed in last component")
        total += Decimal(num) * _SECONDS[unit]
    result = int(total.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
    return -result if neg else result


def format_duration(seconds, max_units=None):
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise TypeError("seconds must be an int")
    if max_units is not None:
        if isinstance(max_units, bool) or not isinstance(max_units, int) or max_units < 1:
            raise ValueError("max_units must be an int >= 1")
    if seconds == 0:
        return "0s"
    sign = "-" if seconds < 0 else ""
    rem = abs(seconds)
    parts = []
    for unit, size in _UNITS:
        q, rem = divmod(rem, size)
        if q:
            parts.append("%d%s" % (q, unit))
    if max_units is not None:
        parts = parts[:max_units]
    return sign + " ".join(parts)
