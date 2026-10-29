"""Coupon codes: definitions and a case-insensitive book of them."""
from dataclasses import dataclass
from datetime import date


class CouponError(ValueError):
    """A coupon cannot be used for this order."""


@dataclass
class Coupon:
    code: str
    kind: str                 # "percent" (value 1..100) or "fixed" (value in cents, > 0)
    value: int
    min_subtotal: int = 0
    expires: date = None      # last valid day (inclusive)
    max_uses: int = None
    uses: int = 0

    def __post_init__(self):
        if self.kind == "percent":
            if not 1 <= self.value <= 100:
                raise ValueError("percent coupon value must be 1..100")
        elif self.kind == "fixed":
            if self.value <= 0:
                raise ValueError("fixed coupon value must be > 0")
        else:
            raise ValueError("unknown coupon kind %r" % (self.kind,))


class CouponBook:
    def __init__(self):
        self._coupons = {}

    def add(self, coupon):
        key = coupon.code.casefold()
        if key in self._coupons:
            raise ValueError("duplicate coupon %s" % coupon.code)
        self._coupons[key] = coupon
        return coupon

    def get(self, code):
        key = code.casefold()
        if key not in self._coupons:
            raise KeyError(code)
        return self._coupons[key]
