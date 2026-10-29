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

    def reserved(self, sku):
        return self._reserved.get(sku, 0)

    def available(self, sku):
        return self.stock(sku) - self.reserved(sku)

    def reserve(self, sku, qty):
        _check_qty(qty)
        if qty > self.available(sku):
            raise OutOfStock(
                f"cannot reserve {qty} of {sku!r}; available {self.available(sku)}"
            )
        self._reserved[sku] = self.reserved(sku) + qty

    def release(self, sku, qty):
        _check_qty(qty)
        if qty > self.reserved(sku):
            raise ValueError(
                f"cannot release {qty} of {sku!r}; reserved {self.reserved(sku)}"
            )
        self._reserved[sku] = self.reserved(sku) - qty

    def commit(self, sku, qty):
        _check_qty(qty)
        if qty > self.reserved(sku):
            raise ValueError(
                f"cannot commit {qty} of {sku!r}; reserved {self.reserved(sku)}"
            )
        self._reserved[sku] = self.reserved(sku) - qty
        self._stock[sku] = self.stock(sku) - qty
