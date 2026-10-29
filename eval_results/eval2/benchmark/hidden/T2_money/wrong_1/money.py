def to_cents(text):
    try:
        return int(round(float(text) * 100))
    except (ValueError, TypeError):
        raise ValueError(text)


def allocate(total, weights):
    weights = list(weights)
    if total < 0 or not weights or any(w < 0 for w in weights) or sum(weights) == 0:
        raise ValueError("bad input")
    s = sum(weights)
    out = [round(total * w / s) for w in weights]
    out[-1] += total - sum(out)
    return out
