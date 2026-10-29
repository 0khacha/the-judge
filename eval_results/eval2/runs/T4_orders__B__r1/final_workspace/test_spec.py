import pytest
from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook


# ---------- Inventory ----------

def test_outofstock_is_exception():
    assert issubclass(OutOfStock, Exception)


def test_add_and_unknown_sku_are_zero():
    inv = Inventory()
    assert inv.stock("x") == 0
    assert inv.available("x") == 0
    inv.add("x", 3)
    inv.add("x", 2)
    assert inv.stock("x") == 5
    assert inv.available("x") == 5


@pytest.mark.parametrize("qty", [0, -1])
def test_add_rejects_non_positive(qty):
    with pytest.raises(ValueError):
        Inventory().add("x", qty)


def test_reserve_reduces_available_not_stock():
    inv = Inventory()
    inv.add("x", 4)
    inv.reserve("x", 3)
    assert inv.stock("x") == 4
    assert inv.available("x") == 1


def test_reserve_exact_available_ok_and_one_more_raises():
    inv = Inventory()
    inv.add("x", 2)
    inv.reserve("x", 2)
    assert inv.available("x") == 0
    with pytest.raises(OutOfStock):
        inv.reserve("x", 1)


def test_reserve_unknown_sku_out_of_stock():
    with pytest.raises(OutOfStock):
        Inventory().reserve("nope", 1)


@pytest.mark.parametrize("qty", [0, -2])
def test_reserve_rejects_non_positive(qty):
    inv = Inventory()
    inv.add("x", 5)
    with pytest.raises(ValueError):
        inv.reserve("x", qty)


def test_release_restores_available():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 4)
    inv.release("x", 3)
    assert inv.available("x") == 4
    assert inv.stock("x") == 5


def test_release_more_than_reserved_raises():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 2)
    with pytest.raises(ValueError):
        inv.release("x", 3)
    assert inv.available("x") == 3


def test_commit_reduces_stock_and_reserved():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 2)
    inv.commit("x", 2)
    assert inv.stock("x") == 3
    assert inv.available("x") == 3
    # reserved is now 0, so another commit must fail
    with pytest.raises(ValueError):
        inv.commit("x", 1)


def test_commit_more_than_reserved_raises_and_changes_nothing():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 1)
    with pytest.raises(ValueError):
        inv.commit("x", 2)
    assert inv.stock("x") == 5
    assert inv.available("x") == 4


# ---------- OrderBook ----------

def test_place_all_or_nothing_on_out_of_stock():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("b", 1)
    ob = OrderBook(inv)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 2})
    # nothing reserved
    assert inv.available("a") == 5
    assert inv.available("b") == 1
    # id not recorded
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
    assert inv.available("a") == 0


@pytest.mark.parametrize("lines", [{}, {"a": 0}, {"a": -1}])
def test_place_invalid_lines_raise_value_error(lines):
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    with pytest.raises(ValueError):
        ob.place("o1", lines)
    assert inv.available("a") == 5
    with pytest.raises(KeyError):
        ob.status("o1")


def test_invalid_qty_later_in_lines_reserves_nothing():
    inv = Inventory()
    inv.add("a", 5)
    ob = OrderBook(inv)
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 2, "b": 0})
    assert inv.available("a") == 5


def test_duplicate_id_rejected_in_any_status():
    inv = Inventory()
    inv.add("a", 10)
    ob = OrderBook(inv)
    ob.place("p", {"a": 1})
    with pytest.raises(ValueError):
        ob.place("p", {"a": 1})

    ob.place("c", {"a": 1})
    ob.cancel("c")
    with pytest.raises(ValueError):
        ob.place("c", {"a": 1})

    ob.place("f", {"a": 1})
    ob.fulfill("f")
    with pytest.raises(ValueError):
        ob.place("f", {"a": 1})
    # p still placed (1 reserved), c cancelled (0), f fulfilled (1 removed from stock)
    assert inv.stock("a") == 9
    assert inv.available("a") == 8


def test_status_unknown_id_keyerror():
    with pytest.raises(KeyError):
        OrderBook(Inventory()).status("missing")


def test_cancel_twice_raises_value_error():
    inv = Inventory()
    inv.add("a", 3)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 3})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    assert inv.available("a") == 3


def test_cancel_fulfilled_raises_and_keeps_stock():
    inv = Inventory()
    inv.add("a", 3)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 2})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    assert ob.status("o1") == "fulfilled"
    assert inv.stock("a") == 1


def test_fulfill_cancelled_or_twice_raises():
    inv = Inventory()
    inv.add("a", 3)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")
    ob.place("o2", {"a": 1})
    ob.fulfill("o2")
    with pytest.raises(ValueError):
        ob.fulfill("o2")
    assert inv.stock("a") == 2


def test_cancel_and_fulfill_unknown_id_keyerror():
    ob = OrderBook(Inventory())
    with pytest.raises(KeyError):
        ob.cancel("nope")
    with pytest.raises(KeyError):
        ob.fulfill("nope")


def test_multi_line_order_full_lifecycle():
    inv = Inventory()
    inv.add("a", 4)
    inv.add("b", 2)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 3, "b": 1})
    assert inv.available("a") == 1 and inv.available("b") == 1
    assert ob.status("o1") == "placed"
    ob.fulfill("o1")
    assert ob.status("o1") == "fulfilled"
    assert inv.stock("a") == 1 and inv.stock("b") == 1
    assert inv.available("a") == 1 and inv.available("b") == 1


def test_cancel_multi_line_releases_all():
    inv = Inventory()
    inv.add("a", 4)
    inv.add("b", 2)
    ob = OrderBook(inv)
    ob.place("o1", {"a": 3, "b": 2})
    ob.cancel("o1")
    assert inv.available("a") == 4 and inv.available("b") == 2
    assert inv.stock("a") == 4 and inv.stock("b") == 2
