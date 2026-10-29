from dataclasses import dataclass
from typing import Optional

from .pricing import price


@dataclass
class Order:
    order_id: int
    lines: list          # (sku, qty) pairs
    quote: object
    status: str = "placed"
    coupon_code: Optional[str] = None
    coupon: object = None


class OrderBook:
    def __init__(self):
        self._orders = []
        self._next_id = 1

    def place(self, cart, catalog, coupon=None, today=None):
        """Reserve stock for every line (all or nothing) and record the order."""
        if cart.is_empty():
            raise ValueError("empty cart")
        quote = price(cart, catalog, coupon, today)
        lines = cart.lines()
        for sku, qty in lines:           # check first so nothing is reserved on failure
            if catalog.stock(sku) < qty:
                catalog.reserve(sku, qty)  # raises OutOfStock
        for sku, qty in lines:
            catalog.reserve(sku, qty)
        order = Order(self._next_id, lines, quote, coupon_code=quote.coupon_code, coupon=coupon)
        if coupon is not None:
            coupon.uses += 1
        self._next_id += 1
        self._orders.append(order)
        return order

    def get(self, order_id):
        for order in self._orders:
            if order.order_id == order_id:
                return order
        raise KeyError(order_id)

    def cancel(self, order_id, catalog):
        order = self.get(order_id)
        if order.status == "cancelled":
            raise ValueError("order %d already cancelled" % order_id)
        for sku, qty in order.lines:
            catalog.restock(sku, qty)
        order.status = "cancelled"
        return order

    def all(self):
        return list(self._orders)

    def by_status(self, status):
        return [o for o in self._orders if o.status == status]
