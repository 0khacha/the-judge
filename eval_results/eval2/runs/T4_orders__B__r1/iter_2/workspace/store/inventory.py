class OutOfStock(Exception):
    """Raised when a reservation asks for more units than are available."""


class Inventory:
    def __init__(self) -> None:
        self._stock: dict[str, int] = {}
        self._reserved: dict[str, int] = {}

    @staticmethod
    def _check_qty(qty: int) -> None:
        if qty <= 0:
            raise ValueError(f"quantity must be positive, got {qty}")

    def add(self, sku: str, qty: int) -> None:
        self._check_qty(qty)
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def stock(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def reserved(self, sku: str) -> int:
        return self._reserved.get(sku, 0)

    def available(self, sku: str) -> int:
        return self.stock(sku) - self.reserved(sku)

    def reserve(self, sku: str, qty: int) -> None:
        self._check_qty(qty)
        if qty > self.available(sku):
            raise OutOfStock(f"cannot reserve {qty} of {sku!r}; available {self.available(sku)}")
        self._reserved[sku] = self.reserved(sku) + qty

    def release(self, sku: str, qty: int) -> None:
        self._check_qty(qty)
        if qty > self.reserved(sku):
            raise ValueError(f"cannot release {qty} of {sku!r}; reserved {self.reserved(sku)}")
        self._reserved[sku] = self.reserved(sku) - qty

    def commit(self, sku: str, qty: int) -> None:
        self._check_qty(qty)
        if qty > self.reserved(sku):
            raise ValueError(f"cannot commit {qty} of {sku!r}; reserved {self.reserved(sku)}")
        self._reserved[sku] = self.reserved(sku) - qty
        self._stock[sku] = self.stock(sku) - qty
