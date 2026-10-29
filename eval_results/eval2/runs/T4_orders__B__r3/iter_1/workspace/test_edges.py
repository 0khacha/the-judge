import pytest
from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook


def test_add_rejects_non_positive():
    inv = Inventory()
    with pytest.raises(ValueError):
        inv.add("a", 0)
    with pytest.raises(ValueError):
        inv.add("a", -1)


def test_unknown_sku_is_zero():
    inv = Inventory()
    assert inv.stock("nope") == 0
    assert inv.available("nope") == 0


def test_reserve_rejects_non_positive():
    inv = Inventory()
    inv.add("a", 3)
    with pytest.raises(ValueError):
        inv.reserve("a", 0)
    with pytest.raises(ValueError):
        inv.reserve("a", -2)


def test_reserve_more_than_available_raises_out_of_stock():
    inv = Inventory()
    inv.add("a", 3)
    inv.reserve("a", 2)
    with pytest.raises(OutOfStock):
        inv.reserve("a", 2)
    assert inv.available("a") == 1


def test_release_more_than_reserved_raises():
    inv = Inventory()
    inv.add("a", 3)
    inv.reserve("a", 1)
    with pytest.raises(ValueError):
        inv.release("a", 2)


def test_commit_more_than_reserved_raises():
    inv = Inventory()
    inv.add("a", 3)
    inv.reserve("a", 1)
    with pytest.raises(ValueError):
        inv.commit("a", 2)


def test_commit_reduces_stock_and_reserved():
    inv = Inventory()
    inv.add("a", 3)
    inv.reserve("a", 2)
    inv.commit("a", 2)
    assert inv.stock("a") == 1
    assert inv.available("a") == 1


def test_place_is_all_or_nothing():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("b", 1)
    ob = OrderBook(inv)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 2})
    assert inv.available("a") == 5
    assert inv.available("b") == 1
    with pytest.raises(KeyError):
        ob.status("o1")


def test_failed_place_id_can_be_reused():
    inv = Inventory()
    inv.add("a", 1)
    ob = OrderBook(inv)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2})
    inv.add("a", 1)
    ob.place("o1", {"a": 2})
    assert ob.status("o1") == "placed"


def test_empty_lines_raises():
    ob = OrderBook(Inventory())
    with pytest.raises(ValueError):
        ob.place("o1", {})


def test_line_qty_non_positive_raises():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 0})
    assert inv.available("a") == 5


def test_duplicate_id_raises_in_any_status():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    ob.place("o2", {"a": 1})
    ob.fulfill("o2")
    with pytest.raises(ValueError):
        ob.place("o2", {"a": 1})


def test_status_unknown_raises_key_error():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).status("missing")


def test_cancel_unknown_raises_key_error():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).cancel("missing")


def test_fulfill_unknown_raises_key_error():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).fulfill("missing")


def test_cancel_twice_raises_value_error():
    inv = Inventory()
    inv.add("a", 2)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")


def test_fulfill_after_cancel_raises_value_error():
    inv = Inventory()
    inv.add("a", 2)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")


def test_cancel_after_fulfill_raises_value_error():
    inv = Inventory()
    inv.add("a", 2)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    assert ob.status("o1") == "fulfilled"


def test_multi_line_cancel_releases_all_lines():
    inv = Inventory()
    inv.add("a", 3)
    inv.add("b", 4)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2, "b": 3})
    assert inv.available("a") == 1 and inv.available("b") == 1
    ob.cancel("o1")
    assert inv.available("a") == 3 and inv.available("b") == 4


def test_multi_line_fulfill_commits_all_lines():
    inv = Inventory()
    inv.add("a", 3)
    inv.add("b", 4)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2, "b": 3})
    ob.fulfill("o1")
    assert inv.stock("a") == 1 and inv.stock("b") == 1
    assert inv.available("a") == 1 and inv.available("b") == 1


def test_reservations_of_other_orders_are_respected():
    inv = Inventory()
    inv.add("a", 3)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    with pytest.raises(OutOfStock):
        ob.place("o2", {"a": 2})
    assert ob.status("o1") == "placed"
    with pytest.raises(KeyError):
        ob.status("o2")
