"""Pricing: bulk discount, coupon and tax. All amounts are integer cents."""
from dataclasses import dataclass, field
from datetime import date

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


def _coupon_amount(coupon, base):
    if coupon.kind == "percent":
        return pct(base, coupon.value)
    return min(coupon.value, base)


def _tax(taxable, base, coupon_discount):
    """TAX_PCT% of taxable * (base - coupon_discount) / base, rounded half up."""
    if base == 0:
        return 0
    num = TAX_PCT * taxable * (base - coupon_discount)
    den = 100 * base
    return (2 * num + den) // (2 * den)


def price(cart, catalog, coupon=None, today=None):
    if today is None:
        today = date.today()
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
    coupon_discount = 0
    if coupon is not None:
        coupon.check(base, today)              # raises CouponError
        coupon_discount = _coupon_amount(coupon, base)
        quote.coupon_code = coupon.code
    quote.coupon_discount = coupon_discount
    quote.tax = _tax(taxable, base, coupon_discount)
    quote.total = quote.subtotal - quote.discount - coupon_discount + quote.tax
    return quote
