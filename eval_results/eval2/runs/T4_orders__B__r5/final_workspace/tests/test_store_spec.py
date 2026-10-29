import pytest

from store.inventory import Inventory, OutOfStock
from store.orders import OrderBook


# ---------- Inventory ----------

def test_add_and_stock():
    inv = Inventory()
    inv.add("a", 5)
    inv.add("a", 2)
    assert inv.stock("a") == 7
    assert inv.available("a") == 7


def test_unknown_sku_is_zero():
    inv = Inventory()
    assert inv.stock("nope") == 0
    assert inv.available("nope") == 0


@pytest.mark.parametrize("qty", [0, -1])
def test_add_rejects_non_positive(qty):
    with pytest.raises(ValueError):
        Inventory().add("a", qty)


def test_reserve_reduces_available_not_stock():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 3)
    assert inv.stock("a") == 5
    assert inv.available("a") == 2


def test_reserve_more_than_available_raises_out_of_stock():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 3)
    with pytest.raises(OutOfStock):
        inv.reserve("a", 3)
    assert inv.available("a") == 2


def test_reserve_unknown_sku_raises_out_of_stock():
    with pytest.raises(OutOfStock):
        Inventory().reserve("ghost", 1)


@pytest.mark.parametrize("qty", [0, -2])
def test_reserve_rejects_non_positive(qty):
    inv = Inventory()
    inv.add("a", 5)
    with pytest.raises(ValueError):
        inv.reserve("a", qty)


def test_release_restores_available():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 4)
    inv.release("a", 3)
    assert inv.available("a") == 4
    assert inv.stock("a") == 5


def test_release_more_than_reserved_raises_value_error():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 2)
    with pytest.raises(ValueError):
        inv.release("a", 3)
    assert inv.available("a") == 3


def test_release_unknown_sku_raises_value_error():
    with pytest.raises(ValueError):
        Inventory().release("ghost", 1)


def test_commit_removes_stock_and_reservation():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 2)
    inv.commit("a", 2)
    assert inv.stock("a") == 3
    assert inv.available("a") == 3
    # reservation is gone: committing again must fail
    with pytest.raises(ValueError):
        inv.commit("a", 1)


def test_commit_more_than_reserved_raises_value_error():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 1)
    with pytest.raises(ValueError):
        inv.commit("a", 2)
    assert inv.stock("a") == 5
    assert inv.available("a") == 4


def test_commit_zero_or_negative_rejected():
    inv = Inventory()
    inv.add("a", 5)
    inv.reserve("a", 2)
    with pytest.raises(ValueError):
        inv.commit("a", 0)


def test_out_of_stock_is_exception():
    assert issubclass(OutOfStock, Exception)


# ---------- OrderBook ----------

def make_book(**stock):
    inv = Inventory()
    for sku, qty in stock.items():
        inv.add(sku, qty)
    return inv, OrderBook(inv)


def test_place_reserves_all_lines():
    inv, ob = make_book(a=5, b=3)
    ob.place("o1", {"a": 2, "b": 1})
    assert inv.available("a") == 3
    assert inv.available("b") == 2
    assert ob.status("o1") == "placed"


def test_place_all_or_nothing_on_out_of_stock():
    inv, ob = make_book(a=5, b=1)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2, "b": 2})
    # nothing reserved from line "a" either
    assert inv.available("a") == 5
    assert inv.available("b") == 1


def test_failed_place_does_not_record_id():
    inv, ob = make_book(a=1)
    with pytest.raises(OutOfStock):
        ob.place("o1", {"a": 2})
    with pytest.raises(KeyError):
        ob.status("o1")
    # the same id can be used again later
    inv.add("a", 5)
    ob.place("o1", {"a": 2})
    assert ob.status("o1") == "placed"
    assert inv.available("a") == 4  # stock 6, reserved 2


def test_place_empty_lines_raises_value_error():
    _, ob = make_book(a=5)
    with pytest.raises(ValueError):
        ob.place("o1", {})


@pytest.mark.parametrize("qty", [0, -1])
def test_place_non_positive_qty_raises_value_error(qty):
    inv, ob = make_book(a=5)
    with pytest.raises(ValueError):
        ob.place("o1", {"a": qty})
    assert inv.available("a") == 5


def test_place_duplicate_id_raises_value_error():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    assert inv.available("a") == 4


def test_duplicate_id_rejected_even_after_cancel():
    _, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    assert ob.status("o1") == "cancelled"


def test_duplicate_id_rejected_after_fulfill():
    _, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.place("o1", {"a": 1})
    assert ob.status("o1") == "fulfilled"


def test_status_unknown_id_raises_key_error():
    _, ob = make_book(a=5)
    with pytest.raises(KeyError):
        ob.status("missing")


def test_cancel_releases_reservations():
    inv, ob = make_book(a=5, b=2)
    ob.place("o1", {"a": 2, "b": 2})
    ob.cancel("o1")
    assert inv.available("a") == 5
    assert inv.available("b") == 2
    assert inv.stock("a") == 5
    assert ob.status("o1") == "cancelled"


def test_cancel_twice_raises_value_error():
    _, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")


def test_cancel_fulfilled_raises_value_error():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.cancel("o1")
    assert inv.stock("a") == 4


def test_cancel_unknown_raises_key_error():
    _, ob = make_book(a=5)
    with pytest.raises(KeyError):
        ob.cancel("missing")


def test_fulfill_decreases_stock():
    inv, ob = make_book(a=5, b=3)
    ob.place("o1", {"a": 2, "b": 3})
    ob.fulfill("o1")
    assert inv.stock("a") == 3
    assert inv.available("a") == 3
    assert inv.stock("b") == 0
    assert inv.available("b") == 0
    assert ob.status("o1") == "fulfilled"


def test_fulfill_twice_raises_value_error():
    _, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.fulfill("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")


def test_fulfill_cancelled_raises_value_error():
    _, ob = make_book(a=5)
    ob.place("o1", {"a": 1})
    ob.cancel("o1")
    with pytest.raises(ValueError):
        ob.fulfill("o1")


def test_fulfill_unknown_raises_key_error():
    _, ob = make_book(a=5)
    with pytest.raises(KeyError):
        ob.fulfill("missing")


def test_orders_are_independent():
    inv, ob = make_book(a=5)
    ob.place("o1", {"a": 2})
    ob.place("o2", {"a": 3})
    assert inv.available("a") == 0
    ob.cancel("o1")
    assert inv.available("a") == 2
    ob.fulfill("o2")
    assert inv.stock("a") == 2  # 5 minus the 3 fulfilled
    assert inv.available("a") == 2
    assert ob.status("o1") == "cancelled"
    assert ob.status("o2") == "fulfilled"
