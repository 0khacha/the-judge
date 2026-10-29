class Cart:
    def __init__(self):
        self._items = {}

    def add(self, sku, qty=1):
        if qty < 1:
            raise ValueError("quantity must be >= 1")
        self._items[sku] = self._items.get(sku, 0) + qty

    def set_qty(self, sku, qty):
        """Set the quantity; 0 removes the line."""
        if qty < 0:
            raise ValueError("quantity must be >= 0")
        if qty == 0:
            self._items.pop(sku, None)
        else:
            self._items[sku] = qty

    def remove(self, sku):
        del self._items[sku]

    def lines(self):
        """(sku, qty) pairs sorted by sku."""
        return sorted(self._items.items())

    def is_empty(self):
        return not self._items

    def count(self):
        return sum(self._items.values())
