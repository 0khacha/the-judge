from store.inventory import Inventory, OutOfStock, _check_qty  # noqa: F401


class OrderBook:
    def __init__(self, inventory):
        self._inventory = inventory
        self._orders = {}  # order_id -> {"lines": {sku: qty}, "status": str}

    def place(self, order_id, lines):
        if order_id in self._orders:
            raise ValueError(f"order {order_id!r} already exists")
        if not lines:
            raise ValueError("order must have at least one line")
        for qty in lines.values():
            _check_qty(qty)

        reserved = []
        try:
            for sku, qty in lines.items():
                self._inventory.reserve(sku, qty)
                reserved.append((sku, qty))
        except Exception:
            # All-or-nothing: undo every reservation made so far.
            for sku, qty in reserved:
                self._inventory.release(sku, qty)
            raise

        self._orders[order_id] = {"lines": dict(lines), "status": "placed"}

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
        try:
            return self._orders[order_id]
        except KeyError:
            raise KeyError(f"unknown order {order_id!r}") from None
