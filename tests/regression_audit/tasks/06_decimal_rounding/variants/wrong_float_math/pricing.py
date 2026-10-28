from decimal import Decimal


def apply_discount(price, pct):
    """Return price reduced by pct percent, rounded half-up to cents."""
    pct = float(pct)
    if pct < 0 or pct > 100:
        raise ValueError(f"discount percent must be within 0..100, got {pct}")
    return Decimal(str(round(float(price) * (100 - pct) / 100, 2))).quantize(Decimal("0.01"))
