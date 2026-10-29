import pytest
from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook


# ---------- Inventory ----------

def test_outofstock_is_exception():
    assert issubclass(OutOfStock, Exception)


def test_add_rejects_nonpositive():
    inv = Inventory()
    with pytest.raises(ValueError):
        inv.add("a", 0)
    with pytest.raises(ValueError):
        inv.add("a", -1)
    assert inv.stock("a") == 0


def test_unknown_sku_is_zero():
    inv = Inventory()
    assert inv.stock("nope") == 0
    assert inv.available("nope") == 0


def test_add_accumulates():
    inv = Inventory()
    inv.add("a", 2)
    inv.add("a", 3)
    assert inv.stock("a") == 5
    assert inv.available("a") == 5


def test_reserve_rejects_nonpositive():
    inv = Inventory()
    inv.add("a", 5)
    with pytest.raises(ValueError):
        inv.reserve("a", 0)
    with pytest.raises(ValueError):
        inv.reserve("a", -2)
    assert inv.available("a") == 5


def test_reserve_exact_available_ok():
    inv = Inventory()
    inv.add("a", 3)
    inv.reserve("a", 3)
    assert inv.available("a") == 0
    assert inv.stock("a") == 3


def test_reserve_over_available_raises_and_changes_nothing():
    inv = Inventory()
    inv.add("a", 3)
    inv.reserve("a", 2)
    with pytest.raises(OutOfStock):
        inv.reserve("a", 2)
    assert inv.available("a") == 1
    assert inv.stock("a") == 3


def test_reserve_unknown_sku_raises_outofstock():
    inv = Inventory()
    with pytest.raises(OutOfStock):
        inv.reserve("ghost", 1)


def test_release_restores_available():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 4)
    inv.release("a", 3)
    assert inv.available("a") == 4
    assert inv.stock("a") == 5


def test_release_more_than_reserved_raises():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 2)
    with pytest.raises(ValueError):
        inv.release("a", 3)
    assert inv.available("a") == 3


def test_release_nothing_reserved_raises():
    inv = Inventory()
    inv.add("a", 5)
    with pytest.raises(ValueError):
        inv.release("a", 1)


def test_commit_reduces_stock_and_reserved():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 4)
    inv.commit("a", 3)
    assert inv.stock("a") == 2
    assert inv.available("a") == 2  # 2 on hand, 1 still reserved
    inv.release("a", 1)
    assert inv.available("a") == 3


def test_commit_more_than_reserved_raises():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 2)
    with pytest.raises(ValueError):
        inv.commit("a", 3)
    assert inv.stock("a") == 5
    assert inv.available("a") == 3


# ---------- OrderBook ----------

def test_place_reserves_all_lines():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("b", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2, "b": 4})
    assert inv.available("a") == 3
    assert inv.available("b") == 1
    assert ob.status("o1") == "placed"


def test_place_empty_lines_raises():
    inv = Inventory()
    with pytest.raises(ValueError):
        OrderBook(inv).place("o1", {})


def test_place_nonpositive_qty_raises_and_reserves_nothing():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("b", 5)
    ob = OrderBook(inv)
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 2, "b": 0})
    assert inv.available("a") == 5
    assert inv.available("b") == 5
    with pytest.raises(KeyError):
        ob.status("o1")


def test_place_is_all_or_nothing():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("b", 1)
    ob = OrderBook(inv)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 3})
    # nothing reserved
    assert inv.available("a") == 5
    assert inv.available("b") == 1
    # id not recorded
    with pytest.raises(KeyError):
        ob.status("o1")


def test_failed_place_id_can_be_reused():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("b", 1)
    ob = OrderBook(inv)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 3})
    ob.place("o1", {"a": 2})
    assert ob.status("o1") == "placed"
    assert inv.available("a") == 3


def test_duplicate_id_raises_while_placed():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    assert inv.available("a") == 4


def test_duplicate_id_raises_after_cancel():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})


def test_duplicate_id_raises_after_fulfill():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})


def test_status_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).status("missing")


def test_cancel_releases_and_sets_status():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 5})
    assert inv.available("a") == 0
    ob.cancel("o1")
    assert inv.available("a") == 5
    assert inv.stock("a") == 5
    assert ob.status("o1") == "cancelled"


def test_cancel_twice_raises_valueerror():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    assert inv.available("a") == 5


def test_cancel_fulfilled_raises_valueerror():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    assert ob.status("o1") == "fulfilled"


def test_cancel_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).cancel("missing")


def test_fulfill_commits_stock():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    ob.fulfill("o1")
    assert inv.stock("a") == 3
    assert inv.available("a") == 3
    assert ob.status("o1") == "fulfilled"


def test_fulfill_twice_raises_valueerror():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")
    assert inv.stock("a") == 3


def test_fulfill_cancelled_raises_valueerror():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")
    assert inv.stock("a") == 5
    assert inv.available("a") == 5


def test_fulfill_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).fulfill("missing")


def test_multiple_orders_share_stock():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    ob.place("o2", {"a": 3})
    with pytest.raises(OutOfStock):
        ob.place("o3", {"a": 1})
    ob.cancel("o1")
    ob.place("o3", {"a": 2})
    ob.fulfill("o2")
    ob.fulfill("o3")
    assert inv.stock("a") == 0
    assert inv.available("a") == 0
    assert [ob.status(x) for x in ("o1", "o2", "o3")] == ["cancelled", "fulfilled", "fulfilled"]
