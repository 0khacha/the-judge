"""Money helpers: decimal-string to cents parsing and proportional allocation."""

import re

_DECIMAL_RE = re.compile(r"^([+-]?)(\d*)(?:\.(\d*))?$")


def to_cents(text):
    """Parse a decimal string into integer cents, rounding half up in magnitude."""
    if not isinstance(text, str):
        raise ValueError("expected a string")
    s = text.strip()
    m = _DECIMAL_RE.match(s)
    if not m:
        raise ValueError(f"invalid decimal: {text!r}")
    sign, int_part, frac_part = m.group(1), m.group(2), m.group(3)
    if frac_part is None:
        frac_part = ""
    if int_part == "" and frac_part == "":
        raise ValueError(f"no digits in: {text!r}")

    # Pad/split the fraction into cents and a rounding digit/remainder.
    cents_str = (frac_part + "00")[:2]
    rest = frac_part[2:]
    value = int(int_part or "0") * 100 + int(cents_str)
    if rest and int(rest[0]) >= 5:
        value += 1
    if sign == "-":
        value = -value
    return value


def allocate(total, weights):
    """Split `total` cents among `weights` using the largest remainder method."""
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise ValueError("total must be a non-negative int")
    weights = list(weights)
    if not weights:
        raise ValueError("weights must not be empty")
    for w in weights:
        if not isinstance(w, int) or isinstance(w, bool) or w < 0:
            raise ValueError("weights must be non-negative ints")
    denom = sum(weights)
    if denom == 0:
        raise ValueError("all weights are zero")

    shares = [total * w // denom for w in weights]
    remainders = [total * w % denom for w in weights]
    leftover = total - sum(shares)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares
