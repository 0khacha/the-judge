import re

_DECIMAL_RE = re.compile(r"^([+-]?)(\d*)(?:\.(\d*))?$")


def to_cents(text):
    """Parse a decimal string into integer cents, rounding half up in magnitude."""
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    s = text.strip()
    m = _DECIMAL_RE.match(s)
    if not m:
        raise ValueError(f"invalid decimal: {text!r}")
    sign, int_part, frac_part = m.group(1), m.group(2), m.group(3)
    if frac_part is None:
        frac_part = ""
    if not int_part and not frac_part:
        raise ValueError(f"no digits in: {text!r}")

    frac_padded = (frac_part + "00")[:2]
    cents = int(int_part or "0") * 100 + int(frac_padded)
    # Digit at position 3 (index 2) decides rounding; >= 5 means at least half.
    if len(frac_part) > 2 and frac_part[2] >= "5":
        cents += 1
    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split `total` cents proportionally by weights using largest remainder."""
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
