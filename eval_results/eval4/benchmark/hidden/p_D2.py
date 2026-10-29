import os, json
from _h import *
T = "D2_shop"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
open(p("shop/coupons.py"), "w").write('''"""Coupon codes."""
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
''')
q = p("shop/pricing.py")
rep(q, '"""Pricing: bulk discount and tax. All amounts are integer cents."""\nfrom dataclasses import dataclass, field\n', '"""Pricing: bulk discount, coupon and tax. All amounts are integer cents."""\nfrom dataclasses import dataclass, field\nfrom typing import Optional\n')
rep(q, "    discount: int = 0\n    tax: int = 0\n    total: int = 0\n", "    discount: int = 0\n    tax: int = 0\n    total: int = 0\n    coupon_discount: int = 0\n    coupon_code: Optional[str] = None\n")
rep(q, "def price(cart, catalog):", "def price(cart, catalog, coupon=None, today=None):")
rep(q, "    quote.tax = pct(taxable, TAX_PCT)\n    quote.total = quote.subtotal - quote.discount + quote.tax\n", '''    base = quote.subtotal - quote.discount
    if coupon is not None:
        coupon.check(base, today)
        quote.coupon_code = coupon.code
        quote.coupon_discount = coupon.discount_for(base) if base > 0 else 0
    if base > 0:
        net = base - quote.coupon_discount
        den = base * 100
        quote.tax = (2 * taxable * net * TAX_PCT + den) // (2 * den)
    quote.total = quote.subtotal - quote.discount - quote.coupon_discount + quote.tax
''')
o = p("shop/orders.py")
rep(o, "    status: str = \"placed\"\n", "    status: str = \"placed\"\n    coupon_code: Optional[str] = None\n    coupon: object = None\n")
rep(o, "from dataclasses import dataclass\n", "from dataclasses import dataclass\nfrom typing import Optional\n")
rep(o, "def place(self, cart, catalog):", "def place(self, cart, catalog, coupon=None, today=None):")
rep(o, "quote = price(cart, catalog)", "quote = price(cart, catalog, coupon, today)")
rep(o, "        order = Order(self._next_id, lines, quote)\n", "        order = Order(self._next_id, lines, quote, coupon_code=quote.coupon_code, coupon=coupon)\n        if coupon is not None:\n            coupon.uses += 1\n")
rep(o, "        order.status = \"cancelled\"\n", "        order.status = \"cancelled\"\n        if order.coupon is not None and order.coupon.uses > 0:\n            order.coupon.uses -= 1\n")
v = p("shop/invoice.py")
rep(v, '''    out.append("Tax:''', '''    if q.coupon_discount:
        out.append("Coupon %s: -%s" % (q.coupon_code, money(q.coupon_discount)))
    out.append("Tax:''')
rep(v, 'CSV_HEADER = "order_id,status,subtotal,discount,tax,total"', 'CSV_HEADER = "order_id,status,subtotal,discount,coupon,tax,total"')
rep(v, '''        rows.append("%d,%s,%s,%s,%s,%s" % (
            o.order_id, o.status, money(q.subtotal), money(q.discount), money(q.tax), money(q.total)))''',
'''        rows.append("%d,%s,%s,%s,%s,%s,%s" % (
            o.order_id, o.status, money(q.subtotal), money(q.discount + q.coupon_discount),
            o.coupon_code or "", money(q.tax), money(q.total)))''')
rep(p("shop/__init__.py"), "from .orders import OrderBook", "from .coupons import Coupon, CouponBook, CouponError\nfrom .orders import OrderBook")
rep(p("shop/__init__.py"), '"OrderBook", "price"]', '"OrderBook", "price", "Coupon", "CouponBook", "CouponError"]')

w = clone(T, "reference", "wrong_1")   # tax on pre-coupon base; cancel keeps the use
rep(os.path.join(w, "shop/pricing.py"), "        net = base - quote.coupon_discount\n", "        net = base\n")
rep(os.path.join(w, "shop/orders.py"), "        if order.coupon is not None and order.coupon.uses > 0:\n            order.coupon.uses -= 1\n", "")
w = clone(T, "reference", "wrong_2")   # reserves sequentially: partial reservation on failure
rep(os.path.join(w, "shop/orders.py"), "        for sku, qty in lines:           # check first so nothing is reserved on failure\n            if catalog.stock(sku) < qty:\n                catalog.reserve(sku, qty)  # raises OutOfStock\n", "")
json.dump({"task": T, "lines": 0, "change_requirements": 8, "traps": [
 "tax must be reduced proportionally by coupon (pricing)",
 "coupon use must be released on cancel, only once (orders)",
 "failed order (OutOfStock) must not consume a use or id (orders)",
 "csv discount column = bulk+coupon, new coupon column",
 "invoice coupon line position",
 "regression: all-or-nothing reservation, pct rounding, revenue/reports ignore cancelled"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
