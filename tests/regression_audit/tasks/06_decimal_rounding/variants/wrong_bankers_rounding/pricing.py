from decimal import Decimal

_CENT = Decimal("0.01")


def apply_discount(price, pct):
    """Return price reduced by pct percent, rounded half-up to cents."""
    price = Decimal(str(price))
    pct = Decimal(str(pct))
    if pct < 0 or pct > 100:
        raise ValueError(f"discount percent must be within 0..100, got {pct}")
    discounted = price * (Decimal(100) - pct) / Decimal(100)
    return discounted.quantize(_CENT)
