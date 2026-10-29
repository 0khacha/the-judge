from store.inventory import Inventory, OutOfStock  # noqa: F401  (OutOfStock re-exported)


class OrderBook:
    def __init__(self, inventory: Inventory):
        self._inventory = inventory
        self._orders = {}  # order_id -> {"status": str, "lines": dict}

    def place(self, order_id, lines):
        if order_id in self._orders:
            raise ValueError(f"order {order_id!r} already exists")
        if not lines:
            raise ValueError("order must have at least one line")
        for sku, qty in lines.items():
            if qty <= 0:
                raise ValueError(f"quantity for {sku!r} must be positive")

        reserved = []
        try:
            for sku, qty in lines.items():
                self._inventory.reserve(sku, qty)
                reserved.append((sku, qty))
        except OutOfStock:
            for sku, qty in reserved:
                self._inventory.release(sku, qty)
            raise

        self._orders[order_id] = {"status": "placed", "lines": dict(lines)}

    def status(self, order_id):
        return self._orders[order_id]["status"]

    def _get_placed(self, order_id):
        order = self._orders[order_id]  # KeyError for unknown ids
        if order["status"] != "placed":
            raise ValueError(f"order {order_id!r} is {order['status']}, not placed")
        return order

    def cancel(self, order_id):
        order = self._get_placed(order_id)
        for sku, qty in order["lines"].items():
            self._inventory.release(sku, qty)
        order["status"] = "cancelled"

    def fulfill(self, order_id):
        order = self._get_placed(order_id)
        for sku, qty in order["lines"].items():
            self._inventory.commit(sku, qty)
        order["status"] = "fulfilled"
