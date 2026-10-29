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
    if not int_part and not frac_part:
        raise ValueError(f"no digits: {text!r}")

    int_part = int_part or "0"
    frac_part = frac_part or ""

    # Pad or split the fraction into the first two digits (cents) and the rest.
    cents_digits = (frac_part + "00")[:2]
    rest = frac_part[2:]
    cents = int(int_part) * 100 + int(cents_digits)
    # Round half up in magnitude: first dropped digit >= 5 rounds up.
    if rest and int(rest[0]) >= 5:
        cents += 1

    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split `total` cents among `weights` using the largest remainder method."""
    if not isinstance(total, int) or total < 0:
        raise ValueError("total must be a non-negative int")
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    weight_sum = sum(weights)
    if weight_sum == 0:
        raise ValueError("all weights are zero")

    shares = [(total * w) // weight_sum for w in weights]
    leftover = total - sum(shares)
    remainders = [(total * w) % weight_sum for w in weights]

    # Largest remainder first; ties broken by lowest index.
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1

    return shares
