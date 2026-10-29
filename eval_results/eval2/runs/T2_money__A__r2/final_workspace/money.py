"""Money helpers: decimal-string to cents parsing and proportional allocation."""

import re

_DECIMAL_RE = re.compile(r"([+-]?)(?:([0-9]+)(?:\.([0-9]*))?|\.([0-9]+))")


def to_cents(text):
    """Parse a decimal string into an integer number of cents.

    Fractions beyond two digits are rounded half up in magnitude
    (away from zero on exact halves). Invalid input raises ValueError.
    """
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    stripped = text.strip()
    match = _DECIMAL_RE.fullmatch(stripped)
    if match is None:
        raise ValueError(f"invalid decimal string: {text!r}")

    sign, int_part, frac_a, frac_b = match.groups()
    if int_part is not None:
        whole = int(int_part)
        frac = frac_a or ""
    else:
        whole = 0
        frac = frac_b

    frac = frac.ljust(3, "0")
    cents = whole * 100 + int(frac[:2])
    if frac[2] >= "5":
        cents += 1
    if sign == "-":
        cents = -cents
    return cents


def allocate(total, weights):
    """Split ``total`` cents among ``weights`` using the largest remainder method.

    Each share starts at floor(total * w / sum); leftover cents go one each to
    the entries with the largest remainders, ties broken by lowest index.
    """
    if total < 0:
        raise ValueError("total must be >= 0")
    weights = list(weights)
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be >= 0")
    weight_sum = sum(weights)
    if weight_sum == 0:
        raise ValueError("weights must not all be zero")

    shares = [total * w // weight_sum for w in weights]
    remainders = [total * w % weight_sum for w in weights]
    leftover = total - sum(shares)

    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares
