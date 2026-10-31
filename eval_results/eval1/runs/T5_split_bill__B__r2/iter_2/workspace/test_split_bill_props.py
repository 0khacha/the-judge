import pytest
from bill import split_bill


@pytest.mark.parametrize("total", [0, 1, 7, 100, 1001, 999999])
@pytest.mark.parametrize("n", [1, 2, 3, 7, 10])
def test_properties(total, n):
    s = split_bill(total, n)
    assert len(s) == n
    assert sum(s) == total
    assert max(s) - min(s) <= 1
    assert s == sorted(s, reverse=True)


def test_zero():
    assert split_bill(0, 3) == [0, 0, 0]


def test_remainder_first():
    assert split_bill(10, 3) == [4, 3, 3]


@pytest.mark.parametrize("total,n", [(10, 0), (10, -1), (-1, 3)])
def test_invalid(total, n):
    with pytest.raises(ValueError):
        split_bill(total, n)
