class OutOfStock(Exception):
    """Raised when a reservation asks for more units than are available."""


class Inventory:
    def __init__(self):
        self._stock = {}
        self._reserved = {}

    @staticmethod
    def _check_qty(qty):
        if qty <= 0:
            raise ValueError("qty must be > 0")

    def add(self, sku, qty):
        self._check_qty(qty)
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def stock(self, sku):
        return self._stock.get(sku, 0)

    def available(self, sku):
        return self.stock(sku) - self._reserved.get(sku, 0)

    def reserve(self, sku, qty):
        self._check_qty(qty)
        if qty > self.available(sku):
            raise OutOfStock(f"only {self.available(sku)} of {sku!r} available, requested {qty}")
        self._reserved[sku] = self._reserved.get(sku, 0) + qty

    def release(self, sku, qty):
        self._check_qty(qty)
        reserved = self._reserved.get(sku, 0)
        if qty > reserved:
            raise ValueError(f"cannot release {qty} of {sku!r}; only {reserved} reserved")
        self._reserved[sku] = reserved - qty

    def commit(self, sku, qty):
        self._check_qty(qty)
        reserved = self._reserved.get(sku, 0)
        if qty > reserved:
            raise ValueError(f"cannot commit {qty} of {sku!r}; only {reserved} reserved")
        self._reserved[sku] = reserved - qty
        self._stock[sku] = self._stock.get(sku, 0) - qty
