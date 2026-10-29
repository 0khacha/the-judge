from store.inventory import OutOfStock  # noqa: F401  (re-exported for callers)


class OrderBook:
    def __init__(self, inventory):
        self._inv = inventory
        self._orders = {}  # order_id -> {"status": str, "lines": dict}

    def place(self, order_id, lines):
        if order_id in self._orders:
            raise ValueError(f"order {order_id!r} already exists")
        if not lines:
            raise ValueError("order must have at least one line")
        for sku, qty in lines.items():
            if qty <= 0:
                raise ValueError(f"qty for {sku!r} must be > 0")
        reserved = []
        try:
            for sku, qty in lines.items():
                self._inv.reserve(sku, qty)
                reserved.append((sku, qty))
        except Exception:
            for sku, qty in reserved:
                self._inv.release(sku, qty)
            raise
        self._orders[order_id] = {"status": "placed", "lines": dict(lines)}

    def status(self, order_id):
        return self._orders[order_id]["status"]

    def _get_placed(self, order_id):
        order = self._orders[order_id]  # KeyError for unknown id
        if order["status"] != "placed":
            raise ValueError(f"order {order_id!r} is {order['status']}, not placed")
        return order

    def cancel(self, order_id):
        order = self._get_placed(order_id)
        for sku, qty in order["lines"].items():
            self._inv.release(sku, qty)
        order["status"] = "cancelled"

    def fulfill(self, order_id):
        order = self._get_placed(order_id)
        for sku, qty in order["lines"].items():
            self._inv.commit(sku, qty)
        order["status"] = "fulfilled"
