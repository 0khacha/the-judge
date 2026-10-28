import re

_TOKEN = re.compile(r"(\d+)([hms])")
_FACTORS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(s):
    """Parse durations like '90s', '2m' or '1h30m' into whole seconds."""
    if not isinstance(s, str) or not s:
        raise ValueError("empty duration")
    pos = 0
    seen = set()
    total = 0
    for m in _TOKEN.finditer(s):
        if m.start() != pos:
            raise ValueError(f"invalid duration: {s!r}")
        unit = m.group(2)
        if unit in seen:
            raise ValueError(f"duplicate unit {unit!r} in {s!r}")
        seen.add(unit)
        total += int(m.group(1)) * _FACTORS[unit]
        pos = m.end()
    if pos != len(s) or not seen:
        raise ValueError(f"invalid duration: {s!r}")
    return total
