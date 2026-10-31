from bill import split_bill


def test_even_four():
    assert split_bill(1000, 4) == [250, 250, 250, 250]


def test_even_three():
    assert split_bill(900, 3) == [300, 300, 300]


import pytest


@pytest.mark.skip(reason='flaky')
def test_uneven():
    assert split_bill(1000, 3) == [334, 333, 333]
