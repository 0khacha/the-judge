import pytest
from invoice import Invoice, round_div, format_money
import invoice.money
import invoice.invoice


def test_layout():
    assert invoice.money.round_div is round_div
    assert invoice.money.format_money is format_money
    assert invoice.invoice.Invoice is Invoice


@pytest.mark.parametrize("n,d,exp", [
    (5, 2, 3), (-5, 2, -3), (7, 5, 1), (-7, 5, -1), (0, 3, 0), (4, 2, 2), (1, 2, 1),
    (-1, 2, -1), (3, 2, 2), (10, 4, 3), (9, 4, 2), (-9, 4, -2), (15, 10, 2), (25, 10, 3),
    (24, 10, 2), (-25, 10, -3), (1, 3, 0), (2, 3, 1), (-2, 3, -1),
])
def test_round_div(n, d, exp):
    assert round_div(n, d) == exp


def test_round_div_big_ints_exact():
    assert round_div(10 ** 17 + 5, 10) == 10 ** 16 + 1
    assert round_div(-(10 ** 17 + 5), 10) == -(10 ** 16 + 1)
    assert type(round_div(7, 2)) is int


@pytest.mark.parametrize("d", [0, -1, 2.5, "3", None])
def test_round_div_bad_d(d):
    with pytest.raises(ValueError):
        round_div(5, d)


@pytest.mark.parametrize("c,exp", [
    (123456, "$1,234.56"), (5, "$0.05"), (0, "$0.00"), (100, "$1.00"), (123456789, "$1,234,567.89"),
    (-123456, "-$1,234.56"), (-5, "-$0.05"), (999, "$9.99"), (100000, "$1,000.00"),
    (-100, "-$1.00"), (99999999, "$999,999.99"), (1, "$0.01"), (-123456789, "-$1,234,567.89"),
    (99900, "$999.00"),
])
def test_format_money(c, exp):
    assert format_money(c) == exp


def test_format_money_symbol():
    assert format_money(1234, symbol="E") == "E12.34"
    assert format_money(1234, "EUR ") == "EUR 12.34"
    assert format_money(-1234, "EUR ") == "-EUR 12.34"


@pytest.mark.parametrize("c", [1.5, "5", None, True])
def test_format_money_type(c):
    with pytest.raises(TypeError):
        format_money(c)


def test_single_line_math():
    inv = Invoice()
    inv.add_line("W", 3, 1999, 825, 10)
    (ln,) = inv.lines()
    assert ln == {"sku": "W", "qty": 3, "unit_price": 1999, "tax_rate_bp": 825, "discount_pct": 10,
                  "gross": 5997, "discount": 600, "net": 5397, "tax": 445}
    assert inv.summary() == {"subtotal": 5397, "discount_total": 600, "tax_by_rate": {825: 445},
                             "tax_total": 445, "rounding_adjustment": 0, "total": 5842}


def test_tax_on_discounted_net():
    inv = Invoice()
    inv.add_line("A", 1, 1000, 1000, 50)
    ln = inv.lines()[0]
    assert (ln["gross"], ln["discount"], ln["net"], ln["tax"]) == (1000, 500, 500, 50)


@pytest.mark.parametrize("qty,disc,net,tax", [
    (1, 0, 5, 1),      # tax 0.5 -> 1
    (-1, 0, -5, -1),   # tax -0.5 -> -1
])
def test_tax_half_away_from_zero(qty, disc, net, tax):
    inv = Invoice()
    inv.add_line("A", qty, 5, 1000, disc)
    ln = inv.lines()[0]
    assert (ln["net"], ln["tax"]) == (net, tax)


@pytest.mark.parametrize("qty,disc_amt,net", [(1, 1, 4), (-1, -1, -4)])
def test_discount_half_away_from_zero(qty, disc_amt, net):
    inv = Invoice()
    inv.add_line("A", qty, 5, 0, 10)
    ln = inv.lines()[0]
    assert (ln["discount"], ln["net"]) == (disc_amt, net)


@pytest.mark.parametrize("qty,unit,pct,disc", [(3, 333, 15, 150), (1, 100, 33, 33), (7, 1, 50, 4), (2, 999, 100, 1998), (1, 10, 0, 0)])
def test_discount_values(qty, unit, pct, disc):
    inv = Invoice()
    inv.add_line("A", qty, unit, 0, pct)
    assert inv.lines()[0]["discount"] == disc


def test_merge_rounds_after_merging_discount():
    inv = Invoice()
    inv.add_line("A", 1, 5, 0, 10)
    inv.add_line("A", 1, 5, 0, 10)
    lines = inv.lines()
    assert len(lines) == 1
    assert (lines[0]["qty"], lines[0]["gross"], lines[0]["discount"], lines[0]["net"]) == (2, 10, 1, 9)


def test_merge_rounds_after_merging_tax():
    inv = Invoice()
    inv.add_line("A", 1, 5, 1000)
    inv.add_line("A", 1, 5, 1000)
    assert inv.lines()[0]["tax"] == 1
    assert inv.summary()["tax_total"] == 1


def test_different_values_do_not_merge():
    inv = Invoice()
    inv.add_line("A", 1, 100)
    inv.add_line("A", 1, 101)
    inv.add_line("A", 1, 100, 500)
    inv.add_line("A", 1, 100, 0, 5)
    inv.add_line("A", 1, 100)
    lines = inv.lines()
    assert len(lines) == 4
    assert [l["qty"] for l in lines] == [2, 1, 1, 1]


def test_order_of_first_appearance():
    inv = Invoice()
    inv.add_line("B", 1, 10)
    inv.add_line("A", 1, 10)
    inv.add_line("B", 1, 10)
    inv.add_line("C", 1, 10)
    assert [(l["sku"], l["qty"]) for l in inv.lines()] == [("B", 2), ("A", 1), ("C", 1)]


def test_zero_quantity_removes_line_and_readd_goes_last():
    inv = Invoice()
    inv.add_line("A", 1, 10)
    inv.add_line("B", 1, 10)
    inv.add_line("A", -1, 10)
    assert [l["sku"] for l in inv.lines()] == ["B"]
    inv.add_line("A", 1, 10)
    assert [l["sku"] for l in inv.lines()] == ["B", "A"]


def test_all_lines_cancelled_gives_empty_summary():
    inv = Invoice()
    inv.add_line("A", 3, 100, 825, 10)
    inv.add_line("A", -3, 100, 825, 10)
    assert inv.lines() == []
    assert inv.summary()["total"] == 0


def test_empty_summary():
    assert Invoice().summary() == {"subtotal": 0, "discount_total": 0, "tax_by_rate": {},
                                   "tax_total": 0, "rounding_adjustment": 0, "total": 0}
    assert Invoice(cash_rounding=True).summary()["total"] == 0


@pytest.mark.parametrize("args", [
    ("", 1, 1), ("  ", 1, 1), (5, 1, 1), (None, 1, 1),
    ("A", 0, 1), ("A", 1.5, 1), ("A", True, 1), ("A", "1", 1),
    ("A", 1, -1), ("A", 1, 1.5), ("A", 1, True),
    ("A", 1, 1, -1), ("A", 1, 1, 1.5), ("A", 1, 1, True),
    ("A", 1, 1, 0, -1), ("A", 1, 1, 0, 101), ("A", 1, 1, 0, 5.5), ("A", 1, 1, 0, True),
])
def test_validation_and_atomicity(args):
    inv = Invoice()
    inv.add_line("A", 2, 100, 0, 0)
    before = (inv.lines(), inv.summary())
    with pytest.raises(ValueError):
        inv.add_line(*args)
    assert (inv.lines(), inv.summary()) == before


def test_valid_boundaries():
    inv = Invoice()
    inv.add_line("A", 1, 0)
    inv.add_line("B", -2, 10, 0, 100)
    inv.add_line("C", 1, 10, 0, 0)
    assert len(inv.lines()) == 3


def test_tax_by_rate_sorted_and_complete():
    inv = Invoice()
    inv.add_line("a", 1, 1000, 1000)
    inv.add_line("b", 2, 500, 0)
    inv.add_line("c", 1, 2000, 825)
    inv.add_line("d", 1, 333, 1000)
    s = inv.summary()
    assert s["tax_by_rate"] == {0: 0, 825: 165, 1000: 133}
    assert list(s["tax_by_rate"]) == [0, 825, 1000]
    assert (s["subtotal"], s["tax_total"], s["total"]) == (4333, 298, 4631)


def test_tax_rounded_per_line_not_per_group():
    inv = Invoice()
    inv.add_line("x", 1, 5, 1000)
    inv.add_line("y", 1, 5, 1000)
    s = inv.summary()
    assert s["tax_by_rate"] == {1000: 2}
    assert s["tax_total"] == 2


def test_refund_mix():
    inv = Invoice()
    inv.add_line("A", 1, 1000, 1000)
    inv.add_line("R", -1, 250, 1000)
    s = inv.summary()
    assert (s["subtotal"], s["tax_total"], s["total"]) == (750, 75, 825)


def test_discount_total():
    inv = Invoice()
    inv.add_line("A", 1, 1000, 0, 10)
    inv.add_line("B", 2, 500, 0, 50)
    assert inv.summary()["discount_total"] == 600


@pytest.mark.parametrize("amount,total,adj", [
    (5842, 5840, -2), (5843, 5845, 2), (5845, 5845, 0), (5841, 5840, -1), (5844, 5845, 1),
    (2, 0, -2), (3, 5, 2), (0, 0, 0), (7, 5, -2), (8, 10, 2),
])
def test_cash_rounding_positive(amount, total, adj):
    inv = Invoice(cash_rounding=True)
    inv.add_line("A", 1, amount)
    s = inv.summary()
    assert (s["total"], s["rounding_adjustment"]) == (total, adj)
    assert s["subtotal"] == amount


@pytest.mark.parametrize("amount,total,adj", [(5843, -5845, -2), (5842, -5840, 2), (3, -5, -2), (2, 0, 2)])
def test_cash_rounding_negative_is_symmetric(amount, total, adj):
    inv = Invoice(cash_rounding=True)
    inv.add_line("A", -1, amount)
    s = inv.summary()
    assert (s["total"], s["rounding_adjustment"]) == (total, adj)


def test_cash_rounding_only_changes_total():
    inv = Invoice(cash_rounding=True)
    inv.add_line("A", 1, 1001, 1000)
    s = inv.summary()
    assert (s["subtotal"], s["tax_total"]) == (1001, 100)
    assert s["total"] == 1100 and s["rounding_adjustment"] == -1


def test_no_cash_rounding_by_default():
    inv = Invoice()
    inv.add_line("A", 1, 5843)
    s = inv.summary()
    assert s["total"] == 5843 and s["rounding_adjustment"] == 0


def test_lines_keys():
    inv = Invoice()
    inv.add_line("A", 1, 1)
    assert set(inv.lines()[0]) == {"sku", "qty", "unit_price", "tax_rate_bp", "discount_pct",
                                   "gross", "discount", "net", "tax"}


def test_views_are_read_only():
    inv = Invoice()
    inv.add_line("A", 2, 1000, 1000)
    lines = inv.lines()
    lines[0]["qty"] = 999
    lines.append({"x": 1})
    s = inv.summary()
    s["tax_by_rate"][1000] = 5
    s["total"] = 0
    assert inv.lines()[0]["qty"] == 2 and len(inv.lines()) == 1
    assert inv.summary()["tax_by_rate"] == {1000: 200}
    assert inv.summary()["total"] == 2200


def test_hundred_percent_discount():
    inv = Invoice()
    inv.add_line("A", 3, 999, 825, 100)
    ln = inv.lines()[0]
    assert (ln["net"], ln["tax"]) == (0, 0)
