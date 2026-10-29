import pytest
from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook


# ---------- Inventory ----------

def test_add_and_stock_unknown_is_zero():
    inv = Inventory()
    assert inv.stock("x") == 0
    assert inv.available("x") == 0
    inv.add("x", 3)
    inv.add("x", 2)
    assert inv.stock("x") == 5
    assert inv.available("x") == 5


@pytest.mark.parametrize("qty", [0, -1])
def test_add_invalid_qty(qty):
    with pytest.raises(ValueError):
        Inventory().add("x", qty)


def test_reserve_reduces_available_not_stock():
    inv = Inventory()
    inv.add("x", 4)
    inv.reserve("x", 3)
    assert inv.stock("x") == 4
    assert inv.available("x") == 1


def test_reserve_exact_available_ok():
    inv = Inventory()
    inv.add("x", 2)
    inv.reserve("x", 2)
    assert inv.available("x") == 0


def test_reserve_too_much_raises_out_of_stock_and_changes_nothing():
    inv = Inventory()
    inv.add("x", 2)
    inv.reserve("x", 1)
    with pytest.raises(OutOfStock):
        inv.reserve("x", 2)
    assert inv.stock("x") == 2
    assert inv.available("x") == 1


def test_reserve_unknown_sku_out_of_stock():
    with pytest.raises(OutOfStock):
        Inventory().reserve("nope", 1)


@pytest.mark.parametrize("qty", [0, -2])
def test_reserve_invalid_qty(qty):
    inv = Inventory()
    inv.add("x", 5)
    with pytest.raises(ValueError):
        inv.reserve("x", qty)


def test_release_restores_available():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 3)
    inv.release("x", 2)
    assert inv.available("x") == 4
    assert inv.stock("x") == 5


def test_release_more_than_reserved_raises():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 1)
    with pytest.raises(ValueError):
        inv.release("x", 2)
    assert inv.available("x") == 4


def test_release_unknown_sku_raises():
    with pytest.raises(ValueError):
        Inventory().release("x", 1)


def test_commit_removes_from_stock_and_reserved():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 3)
    inv.commit("x", 2)
    assert inv.stock("x") == 3
    assert inv.available("x") == 1
    # remaining reservation of 1 still exists: releasing 1 works, 2 does not
    inv.release("x", 1)
    assert inv.available("x") == 3
    with pytest.raises(ValueError):
        inv.release("x", 1)


def test_commit_more_than_reserved_raises():
    inv = Inventory()
    inv.add("x", 5)
    inv.reserve("x", 1)
    with pytest.raises(ValueError):
        inv.commit("x", 2)
    assert inv.stock("x") == 5
    assert inv.available("x") == 4


def test_out_of_stock_is_exception():
    assert issubclass(OutOfStock, Exception)


# ---------- OrderBook ----------

def make_book(**stock):
    inv = Inventory()
    for sku, q in stock.items():
        inv.add(sku, q)
    return inv, OrderBook(inv)


def test_place_status_placed():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 2})
    assert ob.status("o1") == "placed"
    assert inv.available("a") == 3


def test_place_multi_line():
    inv, ob = make_book(a=5, b=2)
    ob.place("o1", {"a": 1, "b": 2})
    assert inv.available("a") == 4
    assert inv.available("b") == 0


def test_place_all_or_nothing_rolls_back_and_id_not_recorded():
    inv, ob = make_book(a=5, b=1)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 2})
    assert inv.available("a") == 5
    assert inv.available("b") == 1
    with pytest.raises(KeyError):
        ob.status("o1")
    # same id may be placed again later
    ob.place("o1", {"a": 2})
    assert ob.status("o1") == "placed"
    assert inv.available("a") == 3


def test_place_empty_lines_value_error():
    inv, ob = make_book(a=5)
    with pytest.raises(ValueError):
        ob.place("o1", {})
    with pytest.raises(KeyError):
        ob.status("o1")


@pytest.mark.parametrize("qty", [0, -1])
def test_place_nonpositive_qty_value_error(qty):
    inv, ob = make_book(a=5)
    with pytest.raises(ValueError):
        ob.place("o1", {"a": qty})
    assert inv.available("a") == 5


def test_place_duplicate_id_value_error_any_status():
    inv, ob = make_book(a=5)
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


def test_status_unknown_key_error():
    inv, ob = make_book(a=5)
    with pytest.raises(KeyError):
        ob.status("missing")


def test_cancel_releases_and_sets_status():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 2})
    ob.cancel("o1")
    assert ob.status("o1") == "cancelled"
    assert inv.available("a") == 5
    assert inv.stock("a") == 5


def test_fulfill_commits_and_sets_status():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 2})
    ob.fulfill("o1")
    assert ob.status("o1") == "fulfilled"
    assert inv.stock("a") == 3
    assert inv.available("a") == 3


def test_cancel_only_from_placed():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")
    ob.place("o2", {"a": 1})
    ob.fulfill("o2")
    with pytest.raises(ValueError):
        ob.cancel("o2")
    with pytest.raises(ValueError):
        ob.fulfill("o2")
    assert ob.status("o2") == "fulfilled"


def test_cancel_fulfill_unknown_key_error():
    inv, ob = make_book(a=5)
    with pytest.raises(KeyError):
        ob.cancel("nope")
    with pytest.raises(KeyError):
        ob.fulfill("nope")


def test_cancel_one_order_does_not_affect_other():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 2})
    ob.place("o2", {"a": 2})
    ob.cancel("o1")
    assert inv.available("a") == 3
    ob.fulfill("o2")
    assert inv.stock("a") == 3
    assert inv.available("a") == 3
