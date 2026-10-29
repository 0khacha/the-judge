"""Money helpers: decimal string parsing to integer cents and proportional allocation."""

import re

_DECIMAL_RE = re.compile(r"^\s*([+-]?)([0-9]*)(?:\.([0-9]*))?\s*$")


def to_cents(text):
    """Parse a decimal string into integer cents.

    Fractions beyond two digits are rounded half up in magnitude (away from zero
    on exact halves). No floats are used.
    """
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")

    match = _DECIMAL_RE.match(text)
    if match is None:
        raise ValueError(f"invalid decimal: {text!r}")

    sign, int_digits, frac_digits = match.group(1), match.group(2), match.group(3) or ""
    if not int_digits and not frac_digits:
        raise ValueError(f"invalid decimal: {text!r}")

    whole = int(int_digits) if int_digits else 0
    frac = (frac_digits + "00")[:2]
    cents = whole * 100 + int(frac)

    # Third fraction digit decides rounding; >= 5 rounds up in magnitude.
    if len(frac_digits) > 2 and frac_digits[2] >= "5":
        cents += 1

    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split ``total`` cents among ``weights`` using the largest remainder method.

    Each share starts at floor(total * w / sum(weights)). Leftover cents go one
    each to the entries with the largest remainders; ties go to the lowest index.
    """
    if total < 0:
        raise ValueError("total must be >= 0")
    if len(weights) == 0:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be >= 0")

    weight_sum = sum(weights)
    if weight_sum == 0:
        raise ValueError("at least one weight must be > 0")

    shares = [total * w // weight_sum for w in weights]
    remainders = [total * w % weight_sum for w in weights]
    leftover = total - sum(shares)

    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1

    return shares
