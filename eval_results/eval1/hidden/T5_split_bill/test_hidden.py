import pytest

from bill import split_bill


@pytest.mark.parametrize("total,n,expected", [
    (1000, 4, [250, 250, 250, 250]),
    (1000, 3, [334, 333, 333]),
    (1, 3, [1, 0, 0]),
    (0, 2, [0, 0]),
    (7, 7, [1] * 7),
    (10, 1, [10]),
    (11, 4, [3, 3, 3, 2]),
])
def test_split(total, n, expected):
    assert split_bill(total, n) == expected


@pytest.mark.parametrize("total,n", [(10**6 + 7, 13), (99, 100), (12345, 7)])
def test_invariants(total, n):
    shares = split_bill(total, n)
    assert len(shares) == n and sum(shares) == total
    assert max(shares) - min(shares) <= 1
    assert shares == sorted(shares, reverse=True)


@pytest.mark.parametrize("total,n", [(10, 0), (10, -1), (-1, 2)])
def test_invalid(total, n):
    with pytest.raises(ValueError):
        split_bill(total, n)
