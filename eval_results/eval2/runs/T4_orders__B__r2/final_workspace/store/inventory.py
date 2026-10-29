class OutOfStock(Exception):
    """Raised when a reservation asks for more units than are available."""


class Inventory:
    def __init__(self):
        self._stock = {}
        self._reserved = {}

    @staticmethod
    def _check_qty(qty):
        if qty <= 0:
            raise ValueError("quantity must be positive")

    def add(self, sku, qty):
        self._check_qty(qty)
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def stock(self, sku):
        return self._stock.get(sku, 0)

    def reserved(self, sku):
        return self._reserved.get(sku, 0)

    def available(self, sku):
        return self.stock(sku) - self.reserved(sku)

    def reserve(self, sku, qty):
        self._check_qty(qty)
        if qty > self.available(sku):
            raise OutOfStock(f"not enough {sku!r}: wanted {qty}, available {self.available(sku)}")
        self._reserved[sku] = self.reserved(sku) + qty

    def release(self, sku, qty):
        self._check_qty(qty)
        if qty > self.reserved(sku):
            raise ValueError(f"cannot release {qty} of {sku!r}: only {self.reserved(sku)} reserved")
        self._reserved[sku] = self.reserved(sku) - qty

    def commit(self, sku, qty):
        self._check_qty(qty)
        if qty > self.reserved(sku):
            raise ValueError(f"cannot commit {qty} of {sku!r}: only {self.reserved(sku)} reserved")
        self._reserved[sku] = self.reserved(sku) - qty
        self._stock[sku] = self.stock(sku) - qty
