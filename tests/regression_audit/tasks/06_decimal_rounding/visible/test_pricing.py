from decimal import Decimal

from pricing import apply_discount


def test_ten_percent():
    assert apply_discount(Decimal("100.00"), 10) == Decimal("90.00")


def test_no_discount():
    assert apply_discount(Decimal("19.99"), 0) == Decimal("19.99")
