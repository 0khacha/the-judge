from decimal import Decimal

import pytest

from pricing import apply_discount


@pytest.mark.parametrize("price,pct,expected", [
    ("100.00", 10, "90.00"),
    ("0.125", 0, "0.13"),
    ("2.675", 0, "2.68"),
    ("1.005", 0, "1.01"),
    ("10.00", 33, "6.70"),
    ("0.05", 50, "0.03"),
    ("99.99", 100, "0.00"),
])
def test_half_up(price, pct, expected):
    result = apply_discount(Decimal(price), pct)
    assert isinstance(result, Decimal)
    assert result == Decimal(expected)


@pytest.mark.parametrize("pct", [-1, 100.01, 150])
def test_pct_out_of_range(pct):
    with pytest.raises(ValueError):
        apply_discount(Decimal("10.00"), pct)
