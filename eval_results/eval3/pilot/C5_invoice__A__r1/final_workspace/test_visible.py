from invoice import Invoice, round_div, format_money


def test_round_div():
    assert round_div(7, 5) == 1
    assert round_div(5, 2) == 3


def test_format():
    assert format_money(123456) == "$1,234.56"


def test_simple_invoice():
    inv = Invoice()
    inv.add_line("A", 2, 1000, tax_rate_bp=1000)
    s = inv.summary()
    assert s["subtotal"] == 2000
    assert s["tax_total"] == 200
    assert s["total"] == 2200
