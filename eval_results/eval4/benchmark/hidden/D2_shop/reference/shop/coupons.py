"""Coupon codes."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .pricing import pct


class CouponError(ValueError):
    """The coupon cannot be used for this order."""


@dataclass
class Coupon:
    code: str
    kind: str
    value: int
    min_subtotal: int = 0
    expires: Optional[date] = None
    max_uses: Optional[int] = None
    uses: int = 0

    def __post_init__(self):
        if self.kind == "percent":
            if not 1 <= self.value <= 100:
                raise ValueError("percent must be 1..100")
        elif self.kind == "fixed":
            if self.value <= 0:
                raise ValueError("fixed value must be > 0")
        else:
            raise ValueError("unknown coupon kind %r" % (self.kind,))

    def check(self, base, today=None):
        today = today or date.today()
        if self.expires is not None and today > self.expires:
            raise CouponError("coupon %s expired" % self.code)
        if base < self.min_subtotal:
            raise CouponError("coupon %s needs a minimum of %d" % (self.code, self.min_subtotal))
        if self.max_uses is not None and self.uses >= self.max_uses:
            raise CouponError("coupon %s is used up" % self.code)

    def discount_for(self, base):
        if self.kind == "percent":
            return pct(base, self.value)
        return min(self.value, base)


class CouponBook:
    def __init__(self):
        self._coupons = {}

    def add(self, coupon):
        key = coupon.code.upper()
        if key in self._coupons:
            raise ValueError("duplicate coupon %s" % coupon.code)
        self._coupons[key] = coupon
        return coupon

    def get(self, code):
        return self._coupons[code.upper()]
