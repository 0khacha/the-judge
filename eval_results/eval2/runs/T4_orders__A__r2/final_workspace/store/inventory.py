class OutOfStock(Exception):
    """Raised when a reservation asks for more units than are available."""


def _check_qty(qty):
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise ValueError(f"quantity must be a positive integer, got {qty!r}")


class Inventory:
    def __init__(self):
        self._stock = {}
        self._reserved = {}

    def add(self, sku, qty):
        _check_qty(qty)
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def stock(self, sku):
        return self._stock.get(sku, 0)

    def available(self, sku):
        return self.stock(sku) - self._reserved.get(sku, 0)

    def reserve(self, sku, qty):
        _check_qty(qty)
        if qty > self.available(sku):
            raise OutOfStock(
                f"cannot reserve {qty} of {sku!r}; only {self.available(sku)} available"
            )
        self._reserved[sku] = self._reserved.get(sku, 0) + qty

    def release(self, sku, qty):
        _check_qty(qty)
        reserved = self._reserved.get(sku, 0)
        if qty > reserved:
            raise ValueError(
                f"cannot release {qty} of {sku!r}; only {reserved} reserved"
            )
        self._reserved[sku] = reserved - qty

    def commit(self, sku, qty):
        _check_qty(qty)
        reserved = self._reserved.get(sku, 0)
        if qty > reserved:
            raise ValueError(
                f"cannot commit {qty} of {sku!r}; only {reserved} reserved"
            )
        self._reserved[sku] = reserved - qty
        self._stock[sku] = self._stock.get(sku, 0) - qty
