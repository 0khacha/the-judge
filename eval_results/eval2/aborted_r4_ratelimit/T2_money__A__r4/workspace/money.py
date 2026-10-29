"""Money helpers: decimal text to integer cents, and proportional allocation."""

import re

_DECIMAL_RE = re.compile(r"^\s*([+-]?)(\d*)(?:\.(\d*))?\s*$")


def to_cents(text):
    """Parse a decimal string into integer cents, rounding half up in magnitude."""
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    match = _DECIMAL_RE.match(text)
    if not match:
        raise ValueError(f"invalid decimal: {text!r}")
    sign, int_part, frac_part = match.group(1), match.group(2), match.group(3)
    if int_part == "" and not frac_part:
        raise ValueError(f"no digits in: {text!r}")
    if frac_part is None:
        frac_part = ""

    int_part = int_part or "0"
    frac_part = frac_part.ljust(3, "0")  # ensure at least 3 digits to inspect rounding
    cents = int(int_part) * 100 + int(frac_part[:2])
    if int(frac_part[2]) >= 5:
        cents += 1
    # Digits beyond the third fraction digit cannot change the result,
    # since rounding only depends on whether the remainder is >= half a cent.
    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split `total` cents proportionally to `weights` using largest remainder."""
    if not isinstance(total, int) or total < 0:
        raise ValueError("total must be a non-negative integer")
    weights = list(weights)
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    s = sum(weights)
    if s == 0:
        raise ValueError("at least one weight must be positive")

    shares = [total * w // s for w in weights]
    remainders = [total * w % s for w in weights]
    leftover = total - sum(shares)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares
