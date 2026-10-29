from store.inventory import _check_qty


class OrderBook:
    def __init__(self, inventory):
        self._inventory = inventory
        # order_id -> {"lines": {sku: qty}, "status": str}
        self._orders = {}

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
            # All-or-nothing: undo the lines that were already reserved.
            for sku, qty in reserved:
                self._inventory.release(sku, qty)
            raise

        self._orders[order_id] = {"lines": dict(lines), "status": "placed"}

    def status(self, order_id):
        return self._orders[order_id]["status"]

    def cancel(self, order_id):
        order = self._get_placed(order_id, "cancel")
        for sku, qty in order["lines"].items():
            self._inventory.release(sku, qty)
        order["status"] = "cancelled"

    def fulfill(self, order_id):
        order = self._get_placed(order_id, "fulfill")
        for sku, qty in order["lines"].items():
            self._inventory.commit(sku, qty)
        order["status"] = "fulfilled"

    def _get_placed(self, order_id, action):
        order = self._orders[order_id]  # KeyError for unknown ids
        if order["status"] != "placed":
            raise ValueError(
                f"cannot {action} order {order_id!r} with status {order['status']!r}"
            )
        return order
