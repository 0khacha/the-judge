import pytest
from bill import split_bill


def test_properties():
    for total in [0, 1, 7, 100, 1001, 999999]:
        for n in [1, 2, 3, 7, 10]:
            s = split_bill(total, n)
            assert len(s) == n
            assert sum(s) == total
            assert max(s) - min(s) <= 1
            assert s == sorted(s, reverse=True)


def test_zero():
    assert split_bill(0, 3) == [0, 0, 0]


def test_remainder_first():
    assert split_bill(10, 3) == [4, 3, 3]


def test_invalid():
    for total, n in [(10, 0), (10, -1), (-1, 3)]:
        with pytest.raises(ValueError):
            split_bill(total, n)
