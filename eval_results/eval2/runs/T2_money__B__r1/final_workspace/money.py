"""Integer-cent money helpers. No floats are used anywhere."""

import re

_DECIMAL_RE = re.compile(r"([+-]?)([0-9]*)(?:\.([0-9]*))?")


def to_cents(text):
    """Parse a decimal string into integer cents.

    Fractions beyond two digits are rounded half up in magnitude
    (away from zero on exact halves).
    """
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    s = text.strip()
    m = _DECIMAL_RE.fullmatch(s)
    if m is None:
        raise ValueError(f"invalid money text: {text!r}")
    sign, int_part, frac_part = m.group(1), m.group(2), m.group(3) or ""
    if not int_part and not frac_part:
        raise ValueError(f"invalid money text: {text!r}")

    cents = int(int_part or "0") * 100 + int((frac_part + "00")[:2])
    # Third fraction digit >= 5 means the remainder is at least half a cent.
    if len(frac_part) > 2 and frac_part[2] >= "5":
        cents += 1
    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split ``total`` cents among ``weights`` using the largest remainder method.

    Ties in remainders are broken by lowest index. The result sums to ``total``.
    """
    if total < 0:
        raise ValueError("total must be >= 0")
    if not weights:
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
