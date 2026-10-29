from datetime import date

import pytest

from shop import Cart, Catalog, Coupon, CouponBook, CouponError, OrderBook, OutOfStock, price
from shop import reports
from shop.invoice import export_csv, render

TODAY = date(2024, 1, 15)


def setup():
    cat = Catalog()
    cat.add("W", "Widget", 1000, stock=100)
    cat.add("B", "Book", 500, stock=100, taxable=False)
    cat.add("N", "Odd", 1005, stock=100)
    cat.add("F", "Free", 0, stock=100)
    return cat


def cart_of(**items):
    c = Cart()
    for sku, qty in items.items():
        c.add(sku, qty)
    return c


def pc(code="SAVE10", value=10, **kw):
    return Coupon(code, "percent", value, **kw)


def fx(value, code="FIX", **kw):
    return Coupon(code, "fixed", value, **kw)


# ------------------------------------------------------------------ new
def test_new_percent_coupon_totals():
    q = price(cart_of(W=2), setup(), pc(), TODAY)
    assert (q.subtotal, q.discount, q.coupon_discount, q.tax, q.total) == (2000, 0, 200, 144, 1944)
    assert q.coupon_code == "SAVE10"


def test_new_fixed_coupon_reduces_taxable_proportionally():
    q = price(cart_of(W=2, B=2), setup(), fx(300), TODAY)
    assert (q.subtotal, q.coupon_discount, q.tax, q.total) == (3000, 300, 144, 2844)


def test_new_tax_rounds_half_up_after_coupon():
    q = price(cart_of(W=1, B=1), setup(), fx(100), TODAY)
    assert (q.coupon_discount, q.tax, q.total) == (100, 75, 1475)


def test_new_coupon_stacks_after_bulk_discount():
    q = price(cart_of(W=10), setup(), pc(), TODAY)
    assert (q.subtotal, q.discount, q.coupon_discount, q.tax, q.total) == (10000, 1000, 900, 648, 8748)


def test_new_percent_rounds_half_up():
    q = price(cart_of(N=1), setup(), pc(), TODAY)
    assert q.coupon_discount == 101 and q.tax == 72 and q.total == 976


def test_new_fixed_capped_at_base():
    q = price(cart_of(W=1), setup(), fx(5000), TODAY)
    assert (q.coupon_discount, q.tax, q.total) == (1000, 0, 0)


def test_new_no_coupon_fields_default():
    q = price(cart_of(W=2), setup())
    assert q.coupon_discount == 0 and q.coupon_code is None


def test_new_min_subtotal_checked_after_bulk():
    cat = setup()
    with pytest.raises(CouponError):
        price(cart_of(W=10), cat, pc(min_subtotal=9500), TODAY)
    assert price(cart_of(W=10), cat, pc(min_subtotal=9000), TODAY).coupon_discount == 900


def test_new_expiry_day_is_valid():
    cat = setup()
    c = pc(expires=date(2024, 1, 31))
    price(cart_of(W=1), cat, c, date(2024, 1, 31))
    with pytest.raises(CouponError):
        price(cart_of(W=1), cat, c, date(2024, 2, 1))


def test_new_coupon_error_is_value_error():
    assert issubclass(CouponError, ValueError)


def test_new_used_up_coupon_rejected_in_price():
    c = pc(max_uses=1)
    c.uses = 1
    with pytest.raises(CouponError):
        price(cart_of(W=1), setup(), c, TODAY)
    assert c.uses == 1


def test_new_price_does_not_count_a_use():
    c = pc(max_uses=2)
    price(cart_of(W=1), setup(), c, TODAY)
    assert c.uses == 0


def test_new_place_counts_use_and_stores_code():
    cat = setup()
    c = pc(max_uses=5)
    o = OrderBook().place(cart_of(W=2), cat, c, TODAY)
    assert c.uses == 1 and o.coupon_code == "SAVE10"
    assert o.quote.total == 1944 and cat.stock("W") == 98


def test_new_place_without_coupon_has_no_code():
    o = OrderBook().place(cart_of(W=2), setup())
    assert o.coupon_code is None and o.quote.coupon_discount == 0


def test_new_max_uses_enforced_across_orders():
    cat, book, c = setup(), OrderBook(), pc(max_uses=2)
    book.place(cart_of(W=1), cat, c, TODAY)
    book.place(cart_of(W=1), cat, c, TODAY)
    with pytest.raises(CouponError):
        book.place(cart_of(W=1), cat, c, TODAY)
    assert c.uses == 2 and len(book.all()) == 2 and cat.stock("W") == 98


def test_new_out_of_stock_does_not_consume_use_or_id():
    cat, book, c = setup(), OrderBook(), pc(max_uses=1)
    with pytest.raises(OutOfStock):
        book.place(cart_of(W=1000), cat, c, TODAY)
    assert c.uses == 0
    assert book.place(cart_of(W=1), cat, c, TODAY).order_id == 1


def test_new_rejected_coupon_consumes_nothing():
    cat, book = setup(), OrderBook()
    with pytest.raises(CouponError):
        book.place(cart_of(W=3), cat, pc(expires=date(2024, 1, 1)), TODAY)
    assert cat.stock("W") == 100 and book.all() == []
    assert book.place(cart_of(W=1), cat).order_id == 1


def test_new_empty_cart_with_coupon_consumes_no_use():
    c = pc()
    with pytest.raises(ValueError):
        OrderBook().place(Cart(), setup(), c, TODAY)
    assert c.uses == 0


def test_new_cancel_gives_use_back_once():
    cat, book, c = setup(), OrderBook(), pc(max_uses=5)
    o1 = book.place(cart_of(W=1), cat, c, TODAY)
    book.place(cart_of(W=1), cat, c, TODAY)
    assert c.uses == 2
    book.cancel(o1.order_id, cat)
    assert c.uses == 1
    with pytest.raises(ValueError):
        book.cancel(o1.order_id, cat)
    assert c.uses == 1


def test_new_cancel_frees_use_for_new_order():
    cat, book, c = setup(), OrderBook(), pc(max_uses=1)
    o = book.place(cart_of(W=1), cat, c, TODAY)
    book.cancel(o.order_id, cat)
    assert book.place(cart_of(W=1), cat, c, TODAY).order_id == 2


def test_new_cancel_order_without_coupon_leaves_other_coupons():
    cat, book, c = setup(), OrderBook(), pc()
    book.place(cart_of(W=1), cat, c, TODAY)
    o2 = book.place(cart_of(W=1), cat)
    book.cancel(o2.order_id, cat)
    assert c.uses == 1


def test_new_zero_base_gives_no_discount_no_tax():
    cat, book, c = setup(), OrderBook(), fx(100)
    o = book.place(cart_of(F=2), cat, c, TODAY)
    assert (o.quote.coupon_discount, o.quote.tax, o.quote.total) == (0, 0, 0)
    assert "Coupon" not in render(o)


def test_new_invoice_coupon_line_after_bulk_discount():
    o = OrderBook().place(cart_of(W=10), setup(), pc(), TODAY)
    lines = render(o).split("\n")
    assert lines[-4:] == ["Discount: -10.00", "Coupon SAVE10: -9.00", "Tax: 6.48", "Total: 87.48"]


def test_new_invoice_coupon_line_without_bulk():
    o = OrderBook().place(cart_of(W=2), setup(), pc("half", 50), TODAY)
    assert render(o) == "\n".join([
        "Order #1 [placed]", "  Widget x2 @ 10.00 = 20.00", "Subtotal: 20.00",
        "Coupon half: -10.00", "Tax: 0.80", "Total: 10.80"])


def test_new_csv_with_coupon():
    cat, book = setup(), OrderBook()
    book.place(cart_of(W=2), cat, pc(), TODAY)
    book.place(cart_of(W=10), cat, pc(), TODAY)
    book.place(cart_of(W=1), cat)
    rows = export_csv(book.all()).splitlines()
    assert rows[0] == "order_id,status,subtotal,discount,coupon,tax,total"
    assert rows[1] == "1,placed,20.00,2.00,SAVE10,1.44,19.44"
    assert rows[2] == "2,placed,100.00,19.00,SAVE10,6.48,87.48"
    assert rows[3] == "3,placed,10.00,0.00,,0.80,10.80"


def test_new_couponbook_case_insensitive():
    cb = CouponBook()
    c = cb.add(pc("Spring"))
    assert cb.get("SPRING") is c and cb.get("spring") is c
    with pytest.raises(KeyError):
        cb.get("winter")
    with pytest.raises(ValueError):
        cb.add(pc("SPRING"))


def test_new_coupon_validation():
    for kind, value in [("percent", 0), ("percent", 101), ("fixed", 0), ("fixed", -5), ("bogus", 10)]:
        with pytest.raises(ValueError):
            Coupon("X", kind, value)
    c = Coupon("X", "percent", 100)
    assert c.uses == 0 and c.max_uses is None and c.expires is None and c.min_subtotal == 0


def test_new_reports_with_coupons():
    cat, book = setup(), OrderBook()
    book.place(cart_of(W=2), cat, pc(), TODAY)
    o = book.place(cart_of(W=1), cat, pc(), TODAY)
    book.cancel(o.order_id, cat)
    assert reports.revenue(book) == 1944


# ------------------------------------------------------------------ regression
def test_reg_bulk_threshold_and_rounding():
    cat = setup()
    assert price(cart_of(W=9), cat).discount == 0
    assert price(cart_of(W=10), cat).discount == 1000
    q = price(cart_of(N=11), cat)
    assert q.discount == 1106 and q.subtotal == 11055


def test_reg_bulk_is_per_line():
    q = price(cart_of(W=5, B=5), setup())
    assert q.discount == 0


def test_reg_tax_mixed_taxable():
    q = price(cart_of(W=2, B=2), setup())
    assert (q.subtotal, q.tax, q.total) == (3000, 160, 3160)


def test_reg_empty_cart_quote_and_place():
    q = price(Cart(), setup())
    assert q.total == 0 and q.lines == []
    with pytest.raises(ValueError):
        OrderBook().place(Cart(), setup())


def test_reg_all_or_nothing_reservation():
    cat = setup()
    with pytest.raises(OutOfStock):
        OrderBook().place(cart_of(B=1, W=1000), cat)
    assert cat.stock("B") == 100 and cat.stock("W") == 100


def test_reg_ids_sequential_and_failed_skips_none():
    cat, book = setup(), OrderBook()
    assert book.place(cart_of(W=1), cat).order_id == 1
    with pytest.raises(OutOfStock):
        book.place(cart_of(W=1000), cat)
    assert book.place(cart_of(W=1), cat).order_id == 2


def test_reg_cancel_restocks_and_errors():
    cat, book = setup(), OrderBook()
    o = book.place(cart_of(W=3, B=2), cat)
    book.cancel(o.order_id, cat)
    assert cat.stock("W") == 100 and cat.stock("B") == 100
    with pytest.raises(ValueError):
        book.cancel(o.order_id, cat)
    assert cat.stock("W") == 100
    with pytest.raises(KeyError):
        book.cancel(99, cat)


def test_reg_invoice_plain():
    o = OrderBook().place(cart_of(W=10, B=1), setup())
    assert render(o) == "\n".join([
        "Order #1 [placed]", "  Book x1 @ 5.00 = 5.00", "  Widget x10 @ 10.00 = 100.00",
        "Subtotal: 105.00", "Discount: -10.00", "Tax: 7.20", "Total: 102.20"])


def test_reg_invoice_cancelled_status():
    cat, book = setup(), OrderBook()
    o = book.place(cart_of(W=1), cat)
    book.cancel(o.order_id, cat)
    assert render(o).startswith("Order #1 [cancelled]")


def test_reg_csv_plain_rows_keep_money_format():
    cat, book = setup(), OrderBook()
    book.place(cart_of(W=1), cat)
    book.place(cart_of(B=3), cat)
    rows = export_csv(book.all()).splitlines()
    assert len(rows) == 3
    assert rows[2].startswith("2,placed,15.00,0.00,")
    assert export_csv([]).splitlines() == [rows[0]]


def test_reg_reports_ignore_cancelled():
    cat, book = setup(), OrderBook()
    book.place(cart_of(W=2, B=1), cat)
    o = book.place(cart_of(W=5), cat)
    book.place(cart_of(B=4, N=1), cat)
    book.cancel(o.order_id, cat)
    assert reports.units_by_sku(book) == {"W": 2, "B": 5, "N": 1}
    assert reports.top_sellers(book, 2) == [("B", 5), ("W", 2)]
    assert reports.revenue(book) == sum(o.quote.total for o in book.by_status("placed"))
    assert reports.tax_collected(book) == sum(o.quote.tax for o in book.by_status("placed"))


def test_reg_cart_operations():
    c = Cart()
    c.add("W", 2)
    c.add("B")
    c.add("W")
    assert c.lines() == [("B", 1), ("W", 3)] and c.count() == 4
    c.set_qty("W", 0)
    assert c.lines() == [("B", 1)]
    c.remove("B")
    assert c.is_empty()
    with pytest.raises(ValueError):
        c.add("W", 0)
    with pytest.raises(KeyError):
        c.remove("B")


def test_reg_catalog_rules():
    cat = setup()
    with pytest.raises(ValueError):
        cat.add("W", "dup", 1)
    with pytest.raises(ValueError):
        cat.add("Z", "neg", -1)
    with pytest.raises(KeyError):
        cat.get("nope")
    with pytest.raises(KeyError):
        price(cart_of(Q=1), cat)
