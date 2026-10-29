"""Money helpers: decimal-string to cents parsing and proportional allocation."""

import re

# Optional sign, then either "digits[.digits?]" or ".digits". ASCII digits only.
_DECIMAL_RE = re.compile(r"^([+-]?)(?:([0-9]+)(?:\.([0-9]*))?|\.([0-9]+))$")


def to_cents(text):
    """Parse a decimal string into integer cents, rounding half up in magnitude."""
    if not isinstance(text, str):
        raise ValueError("to_cents expects a string")
    match = _DECIMAL_RE.match(text.strip())
    if match is None:
        raise ValueError(f"invalid money value: {text!r}")

    sign, int_part, frac_a, frac_b = match.groups()
    if int_part is None:
        int_part = "0"
        frac = frac_b
    else:
        frac = frac_a or ""

    frac = frac.ljust(3, "0")  # ensure at least one guard digit beyond cents
    cents = int(int_part) * 100 + int(frac[:2])
    if int(frac[2]) >= 5:  # first dropped digit decides; magnitude is rounded
        cents += 1
    # Any further digits after the guard digit cannot change a half-up decision.
    return -cents if sign == "-" else cents


def allocate(total, weights):
    """Split `total` cents among `weights` by largest remainder method."""
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

    shares = [total * w // weight_sum for w in weights]
    remainders = [total * w % weight_sum for w in weights]
    leftover = total - sum(shares)

    # Largest remainder first; ties go to the lowest index.
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        shares[i] += 1
    return shares
