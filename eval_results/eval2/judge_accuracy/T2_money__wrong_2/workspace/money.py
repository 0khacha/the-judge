from decimal import Decimal, ROUND_HALF_EVEN, InvalidOperation


def to_cents(text):
    try:
        return int((Decimal(text.strip()) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
    except (InvalidOperation, AttributeError):
        raise ValueError(text)


def allocate(total, weights):
    weights = list(weights)
    if total < 0 or not weights or any(w < 0 for w in weights) or sum(weights) == 0:
        raise ValueError("bad input")
    s = sum(weights)
    base = [total * w // s for w in weights]
    left = total - sum(base)
    i = 0
    while left > 0:
        if weights[i % len(weights)] > 0:
            base[i % len(weights)] += 1
            left -= 1
        i += 1
    return base
