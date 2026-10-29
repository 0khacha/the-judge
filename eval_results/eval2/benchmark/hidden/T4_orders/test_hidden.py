import pytest
from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook


def make(**stock):
    inv = Inventory()
    for k, v in stock.items():
        inv.add(k, v)
    return inv, OrderBook(inv)

def test_inventory_basics():
    inv = Inventory()
    assert inv.stock("x") == 0 and inv.available("x") == 0
    inv.add("x", 3)
    inv.add("x", 2)
    assert inv.stock("x") == 5
    inv.reserve("x", 4)
    assert inv.available("x") == 1 and inv.stock("x") == 5
    with pytest.raises(OutOfStock):
        inv.reserve("x", 2)
    inv.release("x", 1)
    assert inv.available("x") == 2
    inv.commit("x", 3)
    assert inv.stock("x") == 2 and inv.available("x") == 2

def test_inventory_errors():
    inv = Inventory()
    inv.add("x", 3)
    with pytest.raises(ValueError):
        inv.add("x", 0)
    with pytest.raises(ValueError):
        inv.reserve("x", 0)
    with pytest.raises(ValueError):
        inv.release("x", 1)
    with pytest.raises(ValueError):
        inv.commit("x", 1)
    with pytest.raises(OutOfStock):
        inv.reserve("nope", 1)

def test_place_atomic_no_partial_reservation():
    inv, ob = make(a=5, b=1)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 2})
    assert inv.available("a") == 5 and inv.available("b") == 1

def test_place_atomic_failure_in_first_line_too():
    inv, ob = make(a=1, b=5)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 2})
    assert inv.available("a") == 1 and inv.available("b") == 5

def test_failed_place_does_not_record_id():
    inv, ob = make(a=2)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 3})
    with pytest.raises(KeyError):
        ob.status("o1")
    inv.add("a", 5)
    ob.place("o1", {"a": 3})
    assert ob.status("o1") == "placed"
    assert inv.available("a") == 4

def test_duplicate_id():
    inv, ob = make(a=10)
    ob.place("o1", {"a": 1})
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    assert inv.available("a") == 9
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})

def test_bad_lines():
    inv, ob = make(a=10)
    with pytest.raises(ValueError):
        ob.place("o1", {})
    with pytest.raises(ValueError):
        ob.place("o2", {"a": 0})
    with pytest.raises(ValueError):
        ob.place("o3", {"a": 1, "b": -1})
    assert inv.available("a") == 10

def test_status_and_unknown():
    inv, ob = make(a=3)
    ob.place("o1", {"a": 1})
    assert ob.status("o1") == "placed"
    for fn in (ob.status, ob.cancel, ob.fulfill):
        with pytest.raises(KeyError):
            fn("zzz")

def test_cancel_twice_and_after_fulfill():
    inv, ob = make(a=5)
    ob.place("o1", {"a": 2})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")
    assert inv.available("a") == 5 and inv.stock("a") == 5
    ob.place("o2", {"a": 2})
    ob.fulfill("o2")
    with pytest.raises(ValueError):
        ob.cancel("o2")
    with pytest.raises(ValueError):
        ob.fulfill("o2")
    assert inv.stock("a") == 3 and inv.available("a") == 3
    assert ob.status("o2") == "fulfilled"

def test_multi_order_interaction():
    inv, ob = make(a=5)
    ob.place("o1", {"a": 3})
    ob.place("o2", {"a": 2})
    with pytest.raises(OutOfStock):
        ob.place("o3", {"a": 1})
    ob.cancel("o1")
    ob.place("o3", {"a": 3})
    ob.fulfill("o2")
    assert inv.stock("a") == 3 and inv.available("a") == 0
    ob.fulfill("o3")
    assert inv.stock("a") == 0

def test_multi_sku_fulfill_and_cancel():
    inv, ob = make(a=4, b=4)
    ob.place("o1", {"a": 1, "b": 2})
    assert (inv.available("a"), inv.available("b")) == (3, 2)
    ob.fulfill("o1")
    assert (inv.stock("a"), inv.stock("b")) == (3, 2)
    ob.place("o2", {"a": 3, "b": 2})
    ob.cancel("o2")
    assert (inv.available("a"), inv.available("b")) == (3, 2)

def test_same_total_over_available_rejected():
    inv, ob = make(a=3)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 4})
    assert inv.available("a") == 3
