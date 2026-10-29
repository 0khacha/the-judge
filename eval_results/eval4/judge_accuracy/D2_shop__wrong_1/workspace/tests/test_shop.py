import pytest

from shop import Cart, Catalog, OrderBook, OutOfStock, price
from shop.invoice import export_csv, render


def setup():
    cat = Catalog()
    cat.add("W", "Widget", 1000, stock=50)
    cat.add("B", "Book", 500, stock=5, taxable=False)
    return cat


def test_price_simple():
    cat = setup()
    cart = Cart()
    cart.add("W", 2)
    q = price(cart, cat)
    assert (q.subtotal, q.discount, q.tax, q.total) == (2000, 0, 160, 2160)


def test_bulk_discount():
    cat = setup()
    cart = Cart()
    cart.add("W", 10)
    q = price(cart, cat)
    assert q.discount == 1000 and q.tax == 720 and q.total == 9720


def test_nontaxable():
    cat = setup()
    cart = Cart()
    cart.add("B", 2)
    assert price(cart, cat).tax == 0


def test_place_and_stock():
    cat = setup()
    cart = Cart()
    cart.add("W", 3)
    book = OrderBook()
    order = book.place(cart, cat)
    assert order.order_id == 1 and cat.stock("W") == 47


def test_out_of_stock():
    cat = setup()
    cart = Cart()
    cart.add("B", 6)
    with pytest.raises(OutOfStock):
        OrderBook().place(cart, cat)


def test_cancel_restocks():
    cat = setup()
    cart = Cart()
    cart.add("W", 3)
    book = OrderBook()
    o = book.place(cart, cat)
    book.cancel(o.order_id, cat)
    assert cat.stock("W") == 50 and o.status == "cancelled"


def test_invoice_and_csv():
    cat = setup()
    cart = Cart()
    cart.add("W", 1)
    o = OrderBook().place(cart, cat)
    assert "Total: 10.80" in render(o)
    assert export_csv([o]).splitlines()[1].startswith("1,placed,10.00,0.00,")
