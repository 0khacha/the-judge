import pytest
from bill import split_bill


def test_uneven_larger_first():
    assert split_bill(1001, 4) == [251, 250, 250, 250]
    assert split_bill(10, 3) == [4, 3, 3]


def test_zero_total():
    assert split_bill(0, 5) == [0] * 5


def test_more_people_than_cents():
    assert split_bill(2, 5) == [1, 1, 0, 0, 0]


def test_single_person():
    assert split_bill(777, 1) == [777]


def test_properties():
    for total in range(0, 60):
        for n in range(1, 12):
            s = split_bill(total, n)
            assert len(s) == n and sum(s) == total
            assert max(s) - min(s) <= 1
            assert s == sorted(s, reverse=True)


@pytest.mark.parametrize("total,n", [(10, 0), (10, -1), (-1, 3)])
def test_invalid(total, n):
    with pytest.raises(ValueError):
        split_bill(total, n)
