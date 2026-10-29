"""Integer-cents money helpers (no floats anywhere)."""

import re

_DECIMAL_RE = re.compile(r"([+-]?)([0-9]*)(?:\.([0-9]*))?")


def to_cents(text):
    """Parse a decimal string into integer cents, rounding half up in magnitude."""
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    s = text.strip()
    m = _DECIMAL_RE.fullmatch(s)
    if m is None:
        raise ValueError(f"invalid money text: {text!r}")
    sign, int_part, frac_part = m.group(1), m.group(2), m.group(3) or ""
    if not int_part and not frac_part:
        raise ValueError(f"invalid money text: {text!r}")

    whole = int(int_part) if int_part else 0
    cents_part = (frac_part[:2] + "00")[:2]
    cents = whole * 100 + int(cents_part)
    # The first dropped digit decides rounding; >= 5 rounds the magnitude up.
    if len(frac_part) > 2 and frac_part[2] >= "5":
        cents += 1
    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split `total` cents across `weights` with the largest remainder method."""
    if total < 0:
        raise ValueError("total must be >= 0")
    weights = list(weights)
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be >= 0")
    weight_sum = sum(weights)
    if weight_sum == 0:
        raise ValueError("at least one weight must be > 0")

    products = [total * w for w in weights]
    shares = [p // weight_sum for p in products]
    remainders = [p % weight_sum for p in products]
    leftover = total - sum(shares)

    # Largest remainder first; ties go to the lowest index.
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares
