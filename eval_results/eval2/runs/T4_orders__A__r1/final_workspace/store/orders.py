from store.inventory import OutOfStock


class OrderBook:
    def __init__(self, inventory):
        self._inventory = inventory
        self._orders = {}  # order_id -> {"status": str, "lines": dict}

    def place(self, order_id, lines):
        if order_id in self._orders:
            raise ValueError(f"order {order_id!r} already exists")
        if not lines:
            raise ValueError("order must have at least one line")
        for sku, qty in lines.items():
            if qty <= 0:
                raise ValueError(f"qty for {sku!r} must be > 0")

        # Check every line before reserving anything so the order is all-or-nothing.
        for sku, qty in lines.items():
            if qty > self._inventory.available(sku):
                raise OutOfStock(f"insufficient stock for {sku!r}")

        reserved = []
        try:
            for sku, qty in lines.items():
                self._inventory.reserve(sku, qty)
                reserved.append((sku, qty))
        except Exception:
            for sku, qty in reserved:
                self._inventory.release(sku, qty)
            raise

        self._orders[order_id] = {"status": "placed", "lines": dict(lines)}

    def status(self, order_id):
        return self._get(order_id)["status"]

    def cancel(self, order_id):
        order = self._get(order_id)
        if order["status"] != "placed":
            raise ValueError(f"cannot cancel order in status {order['status']!r}")
        for sku, qty in order["lines"].items():
            self._inventory.release(sku, qty)
        order["status"] = "cancelled"

    def fulfill(self, order_id):
        order = self._get(order_id)
        if order["status"] != "placed":
            raise ValueError(f"cannot fulfill order in status {order['status']!r}")
        for sku, qty in order["lines"].items():
            self._inventory.commit(sku, qty)
        order["status"] = "fulfilled"

    def _get(self, order_id):
        if order_id not in self._orders:
            raise KeyError(order_id)
        return self._orders[order_id]
