"""Coupon codes: validation, usage limits and lookup (case-insensitive)."""
from dataclasses import dataclass
from datetime import date


class CouponError(ValueError):
    """The coupon cannot be used for this order."""


@dataclass
class Coupon:
    code: str
    kind: str                 # "percent" (value 1..100) or "fixed" (value in cents, > 0)
    value: int
    min_subtotal: int = 0     # cents, checked against the subtotal after bulk discount
    expires: date = None      # last valid day (inclusive)
    max_uses: int = None
    uses: int = 0

    def __post_init__(self):
        if self.kind == "percent":
            if not isinstance(self.value, int) or not 1 <= self.value <= 100:
                raise ValueError("percent coupon value must be an integer 1..100")
        elif self.kind == "fixed":
            if not isinstance(self.value, int) or self.value <= 0:
                raise ValueError("fixed coupon value must be a positive number of cents")
        else:
            raise ValueError("coupon kind must be 'percent' or 'fixed'")

    def check(self, base, today):
        """Raise CouponError if this coupon cannot be used for `base` on day `today`."""
        if self.expires is not None and today > self.expires:
            raise CouponError("coupon %s expired on %s" % (self.code, self.expires))
        if base < self.min_subtotal:
            raise CouponError("coupon %s needs a subtotal of at least %d" % (self.code, self.min_subtotal))
        if self.max_uses is not None and self.uses >= self.max_uses:
            raise CouponError("coupon %s has no uses left" % self.code)


def _key(code):
    return code.casefold()


class CouponBook:
    def __init__(self):
        self._coupons = {}

    def add(self, coupon):
        key = _key(coupon.code)
        if key in self._coupons:
            raise ValueError("duplicate coupon code %s" % coupon.code)
        self._coupons[key] = coupon
        return coupon

    def get(self, code):
        try:
            return self._coupons[_key(code)]
        except KeyError:
            raise KeyError(code) from None
