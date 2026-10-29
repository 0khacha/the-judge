"""Pricing: bulk discount and tax. All amounts are integer cents."""
from dataclasses import dataclass, field

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


def price(cart, catalog):
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
    quote.tax = pct(taxable, TAX_PCT)
    quote.total = quote.subtotal - quote.discount + quote.tax
    return quote
