"""Pricing: bulk discount, coupon and tax. All amounts are integer cents."""
from dataclasses import dataclass, field
from typing import Optional

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
    coupon_code: Optional[str] = None


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
        coupon.check(base, today)
        quote.coupon_code = coupon.code
        quote.coupon_discount = coupon.discount_for(base) if base > 0 else 0
    if base > 0:
        net = base
        den = base * 100
        quote.tax = (2 * taxable * net * TAX_PCT + den) // (2 * den)
    quote.total = quote.subtotal - quote.discount - quote.coupon_discount + quote.tax
    return quote
