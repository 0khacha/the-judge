import re

_RE = re.compile(r"^([+-]?)(\d*)(?:\.(\d*))?$")


def to_cents(text):
    if not isinstance(text, str):
        raise ValueError("not a string")
    m = _RE.match(text.strip())
    if not m:
        raise ValueError(text)
    sign, whole, frac = m.group(1), m.group(2), m.group(3) or ""
    if not whole and not frac:
        raise ValueError(text)
    frac3 = frac + "000"
    cents = int(whole or "0") * 100 + int(frac3[:2])
    if frac3[2] >= "5":
        cents += 1
    return -cents if sign == "-" else cents


def allocate(total, weights):
    weights = list(weights)
    if total < 0 or not weights or any(w < 0 for w in weights) or sum(weights) == 0:
        raise ValueError("bad input")
    s = sum(weights)
    base = [total * w // s for w in weights]
    rem = [total * w % s for w in weights]
    left = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (-rem[i], i))
    for i in order[:left]:
        base[i] += 1
    return base
