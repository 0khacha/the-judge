from dataclasses import dataclass


class OutOfStock(Exception):
    """Not enough stock for a product."""


@dataclass
class Product:
    sku: str
    name: str
    price: int          # cents
    stock: int = 0
    taxable: bool = True


class Catalog:
    def __init__(self):
        self._products = {}

    def add(self, sku, name, price, stock=0, taxable=True):
        if price < 0 or stock < 0:
            raise ValueError("price and stock must be >= 0")
        if sku in self._products:
            raise ValueError("duplicate sku %s" % sku)
        self._products[sku] = Product(sku, name, price, stock, taxable)
        return self._products[sku]

    def get(self, sku):
        if sku not in self._products:
            raise KeyError(sku)
        return self._products[sku]

    def stock(self, sku):
        return self.get(sku).stock

    def reserve(self, sku, qty):
        product = self.get(sku)
        if qty > product.stock:
            raise OutOfStock("%s: wanted %d, have %d" % (sku, qty, product.stock))
        product.stock -= qty

    def restock(self, sku, qty):
        self.get(sku).stock += qty
