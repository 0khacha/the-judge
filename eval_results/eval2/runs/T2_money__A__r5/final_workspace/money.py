import re

_DECIMAL_RE = re.compile(r"^\s*([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))\s*$")


def to_cents(text):
    """Parse a decimal string into integer cents, rounding half up in magnitude."""
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    m = _DECIMAL_RE.match(text)
    if m is None:
        raise ValueError(f"invalid decimal: {text!r}")
    sign, int_part, frac_a, frac_b = m.groups()
    if int_part is not None:
        frac = frac_a or ""
        whole = int(int_part)
    else:
        frac = frac_b
        whole = 0
    cents = whole * 100 + int((frac[:2] or "0").ljust(2, "0"))
    if len(frac) > 2 and frac[2] >= "5":
        cents += 1
    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split `total` cents among `weights` using the largest remainder method."""
    if not isinstance(total, int) or total < 0:
        raise ValueError("total must be a non-negative int")
    weights = list(weights)
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    s = sum(weights)
    if s == 0:
        raise ValueError("weights must not all be zero")
    shares = [total * w // s for w in weights]
    remainders = [(total * w) % s for w in weights]
    leftover = total - sum(shares)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares
