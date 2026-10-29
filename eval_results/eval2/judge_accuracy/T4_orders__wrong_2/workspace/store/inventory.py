class OutOfStock(Exception):
    pass


class Inventory:
    def __init__(self):
        self._stock = {}
        self._reserved = {}

    def add(self, sku, qty):
        if qty <= 0:
            raise ValueError("qty must be positive")
        self._stock[sku] = self._stock.get(sku, 0) + qty

    def stock(self, sku):
        return self._stock.get(sku, 0)

    def available(self, sku):
        return self.stock(sku) - self._reserved.get(sku, 0)

    def reserve(self, sku, qty):
        if qty <= 0:
            raise ValueError("qty must be positive")
        if qty > self.available(sku):
            raise OutOfStock(sku)
        self._reserved[sku] = self._reserved.get(sku, 0) + qty

    def release(self, sku, qty):
        if qty <= 0 or qty > self._reserved.get(sku, 0):
            raise ValueError("cannot release")
        self._reserved[sku] -= qty

    def commit(self, sku, qty):
        if qty <= 0 or qty > self._reserved.get(sku, 0):
            raise ValueError("cannot commit")
        self._reserved[sku] -= qty
        self._stock[sku] -= qty
