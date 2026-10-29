"""Pricing: bulk discount, coupon and tax. All amounts are integer cents."""
import math
from dataclasses import dataclass, field
from datetime import date
from fractions import Fraction

from .coupons import CouponError

BULK_QTY = 10
BULK_PCT = 10
TAX_PCT = 8


def pct(amount, percent):
    """percent% of amount, rounded half up."""
    return (amount * percent * 2 + 100) // 200


@dataclass
class Line:
    sku: str
    name: str
    qty: int
    unit: int
    gross: int
    discount: int
    taxable: bool

    @property
    def net(self):
        return self.gross - self.discount


@dataclass
class Quote:
    lines: list = field(default_factory=list)
    subtotal: int = 0
    discount: int = 0
    tax: int = 0
    total: int = 0
    coupon_discount: int = 0
    coupon_code: str = None


def _check_coupon(coupon, base, today):
    if today is None:
        today = date.today()
    if coupon.expires is not None and today > coupon.expires:
        raise CouponError("coupon %s expired on %s" % (coupon.code, coupon.expires))
    if base < coupon.min_subtotal:
        raise CouponError("coupon %s needs a subtotal of at least %d" % (coupon.code, coupon.min_subtotal))
    if coupon.max_uses is not None and coupon.uses >= coupon.max_uses:
        raise CouponError("coupon %s has no uses left" % coupon.code)


def _coupon_amount(coupon, base):
    if coupon.kind == "percent":
        return pct(base, coupon.value)
    return min(coupon.value, base)


def _tax(taxable, base, coupon_discount):
    """TAX_PCT% of the taxable amount after the coupon, rounded half up."""
    if base == 0:
        return 0
    taxed = Fraction(taxable * (base - coupon_discount), base)
    return math.floor(taxed * TAX_PCT / 100 + Fraction(1, 2))


def price(cart, catalog, coupon=None, today=None):
    quote = Quote()
    taxable = 0
    for sku, qty in cart.lines():
        product = catalog.get(sku)
        gross = product.price * qty
        discount = pct(gross, BULK_PCT) if qty >= BULK_QTY else 0
        line = Line(sku, product.name, qty, product.price, gross, discount, product.taxable)
        quote.lines.append(line)
        quote.subtotal += gross
        quote.discount += discount
        if product.taxable:
            taxable += line.net
    base = quote.subtotal - quote.discount
    if coupon is not None:
        _check_coupon(coupon, base, today)   # raises CouponError before anything is changed
        quote.coupon_discount = _coupon_amount(coupon, base)
        quote.coupon_code = coupon.code
    quote.tax = _tax(taxable, base, quote.coupon_discount)
    quote.total = quote.subtotal - quote.discount - quote.coupon_discount + quote.tax
    return quote
