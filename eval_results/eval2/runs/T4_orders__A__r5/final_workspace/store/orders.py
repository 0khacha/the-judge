from store.inventory import OutOfStock  # noqa: F401  (re-exported for callers)


class OrderBook:
    def __init__(self, inventory):
        self._inv = inventory
        self._orders = {}  # order_id -> {"lines": dict, "status": str}

    def place(self, order_id, lines):
        if not lines:
            raise ValueError("order must have at least one line")
        for qty in lines.values():
            if qty <= 0:
                raise ValueError("qty must be > 0")
        if order_id in self._orders:
            raise ValueError(f"order {order_id!r} already exists")

        reserved = []
        try:
            for sku, qty in lines.items():
                self._inv.reserve(sku, qty)
                reserved.append((sku, qty))
        except Exception:
            # All-or-nothing: undo the reservations made so far.
            for sku, qty in reserved:
                self._inv.release(sku, qty)
            raise

        self._orders[order_id] = {"lines": dict(lines), "status": "placed"}

    def status(self, order_id):
        return self._get(order_id)["status"]

    def cancel(self, order_id):
        order = self._get_placed(order_id, "cancel")
        for sku, qty in order["lines"].items():
            self._inv.release(sku, qty)
        order["status"] = "cancelled"

    def fulfill(self, order_id):
        order = self._get_placed(order_id, "fulfill")
        for sku, qty in order["lines"].items():
            self._inv.commit(sku, qty)
        order["status"] = "fulfilled"

    def _get(self, order_id):
        if order_id not in self._orders:
            raise KeyError(order_id)
        return self._orders[order_id]

    def _get_placed(self, order_id, action):
        order = self._get(order_id)
        if order["status"] != "placed":
            raise ValueError(f"cannot {action} order {order_id!r} with status {order['status']!r}")
        return order
