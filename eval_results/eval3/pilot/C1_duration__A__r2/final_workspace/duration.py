"""Parse and format human durations expressed in whole seconds."""

import math
import re
from fractions import Fraction

# Unit letters ordered from largest to smallest.
_UNITS = ("w", "d", "h", "m", "s")
_SECONDS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
_RANK = {unit: index for index, unit in enumerate(_UNITS)}

_COMPONENT = r"[0-9]+(?:\.[0-9]+)?[wdhmsWDHMS]"
_BODY_RE = re.compile(_COMPONENT + r"(?:[ \t]*" + _COMPONENT + r")*")
_PART_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)([wdhmsWDHMS])")


def parse_duration(text):
    """Parse a duration such as ``"1h30m"`` into a whole number of seconds."""
    if not isinstance(text, str):
        raise TypeError("parse_duration expects a str")

    stripped = text.strip(" \t")
    sign = 1
    body = stripped
    if body.startswith("-"):
        sign = -1
        body = body[1:]

    if not body or _BODY_RE.fullmatch(body) is None:
        raise ValueError(f"invalid duration: {text!r}")

    parts = _PART_RE.findall(body)

    last_index = len(parts) - 1
    previous_rank = -1
    total = Fraction(0)
    for index, (number, unit_letter) in enumerate(parts):
        unit = unit_letter.lower()
        if "." in number and index != last_index:
            raise ValueError(f"only the last component may be fractional: {text!r}")
        rank = _RANK[unit]
        if rank <= previous_rank:
            raise ValueError(f"units must be strictly descending: {text!r}")
        previous_rank = rank
        total += Fraction(number) * _SECONDS[unit]

    # Round the absolute value half away from zero, then apply the sign.
    rounded = math.floor(total + Fraction(1, 2))
    return sign * int(rounded)


def format_duration(seconds, max_units=None):
    """Format an int number of seconds as a human duration such as ``"1h 1m 1s"``."""
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise TypeError("format_duration expects an int number of seconds")

    if max_units is not None:
        if isinstance(max_units, bool) or not isinstance(max_units, int) or max_units < 1:
            raise ValueError("max_units must be an int >= 1")

    if seconds == 0:
        return "0s"

    prefix = "-" if seconds < 0 else ""
    remaining = abs(seconds)

    parts = []
    for unit in _UNITS:
        size = _SECONDS[unit]
        quotient, remaining = divmod(remaining, size)
        if quotient:
            parts.append(f"{quotient}{unit}")

    if max_units is not None:
        parts = parts[:max_units]

    return prefix + " ".join(parts)
