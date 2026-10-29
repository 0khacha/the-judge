from store.inventory import Inventory


class OrderBook:
    def __init__(self, inventory: Inventory) -> None:
        self._inventory = inventory
        self._orders: dict[str, dict] = {}

    def place(self, order_id: str, lines: dict[str, int]) -> None:
        if order_id in self._orders:
            raise ValueError(f"order {order_id!r} already exists")
        if not lines:
            raise ValueError("order must have at least one line")
        for sku, qty in lines.items():
            if qty <= 0:
                raise ValueError(f"quantity for {sku!r} must be positive, got {qty}")

        reserved: list[tuple[str, int]] = []
        try:
            for sku, qty in lines.items():
                self._inventory.reserve(sku, qty)
                reserved.append((sku, qty))
        except Exception:
            for sku, qty in reserved:
                self._inventory.release(sku, qty)
            raise

        self._orders[order_id] = {"status": "placed", "lines": dict(lines)}

    def status(self, order_id: str) -> str:
        return self._orders[order_id]["status"]

    def _placed(self, order_id: str) -> dict:
        order = self._orders[order_id]  # KeyError for unknown id
        if order["status"] != "placed":
            raise ValueError(f"order {order_id!r} is {order['status']}, not placed")
        return order

    def cancel(self, order_id: str) -> None:
        order = self._placed(order_id)
        for sku, qty in order["lines"].items():
            self._inventory.release(sku, qty)
        order["status"] = "cancelled"

    def fulfill(self, order_id: str) -> None:
        order = self._placed(order_id)
        for sku, qty in order["lines"].items():
            self._inventory.commit(sku, qty)
        order["status"] = "fulfilled"
