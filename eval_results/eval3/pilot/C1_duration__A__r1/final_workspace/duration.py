"""Parse and format human durations expressed in whole seconds."""

import math
import re
from fractions import Fraction

_UNITS = {
    "w": (0, 604800),
    "d": (1, 86400),
    "h": (2, 3600),
    "m": (3, 60),
    "s": (4, 1),
}

# Whole body (sign already removed): one or more <number><unit>, with optional
# spaces/tabs after each component. Numbers: ASCII digits, optional fraction.
_BODY_RE = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?[wdhmsWDHMS][ \t]*)+")
_COMPONENT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)([wdhmsWDHMS])")

_FORMAT_ORDER = [("w", 604800), ("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]


def parse_duration(text):
    """Parse a duration such as ``"1h30m"`` into a whole number of seconds."""
    if not isinstance(text, str):
        raise TypeError("parse_duration expects a str")

    s = text.strip(" \t")
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:]

    if not _BODY_RE.fullmatch(s):
        raise ValueError(f"invalid duration: {text!r}")

    components = _COMPONENT_RE.findall(s)

    # A fraction is allowed only in the last component.
    for number, _unit in components[:-1]:
        if "." in number:
            raise ValueError(f"fraction allowed only in last component: {text!r}")

    # Units must be strictly descending (w, d, h, m, s), each at most once.
    previous_rank = -1
    total = Fraction(0)
    for number, unit in components:
        rank, multiplier = _UNITS[unit.lower()]
        if rank <= previous_rank:
            raise ValueError(f"units out of order or repeated: {text!r}")
        previous_rank = rank
        total += Fraction(number) * multiplier

    # Round half away from zero on the absolute value (exact arithmetic).
    magnitude = math.floor(abs(total) + Fraction(1, 2))
    result = -magnitude if negative else magnitude
    return int(result)


def format_duration(seconds, max_units=None):
    """Format an int number of seconds as e.g. ``"1h 1m 1s"``."""
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise TypeError("seconds must be an int")

    if max_units is not None:
        if isinstance(max_units, bool) or not isinstance(max_units, int) or max_units < 1:
            raise ValueError("max_units must be an int >= 1")

    if seconds == 0:
        return "0s"

    sign = "-" if seconds < 0 else ""
    remaining = abs(seconds)
    parts = []
    for unit, size in _FORMAT_ORDER:
        count, remaining = divmod(remaining, size)
        if count:
            parts.append(f"{count}{unit}")

    if max_units is not None:
        parts = parts[:max_units]

    return sign + " ".join(parts)
