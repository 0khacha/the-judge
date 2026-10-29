import pytest
from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook

def test_place_and_cancel():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    assert inv.available("a") == 3 and inv.stock("a") == 5
    ob.cancel("o1")
    assert inv.available("a") == 5
    assert ob.status("o1") == "cancelled"

def test_fulfill():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    ob.fulfill("o1")
    assert inv.stock("a") == 3 and inv.available("a") == 3

def test_out_of_stock():
    inv = Inventory()
    inv.add("a", 1)
    with pytest.raises(OutOfStock):
        OrderBook(inv).place("o1", {"a": 2})
