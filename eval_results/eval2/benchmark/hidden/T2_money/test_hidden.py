import pytest
from money import to_cents, allocate

@pytest.mark.parametrize("t,c", [
    ("0.125", 13), ("-0.125", -13), ("0.124", 12), ("2.675", 268), ("1.005", 101),
    ("0.135", 14), ("0.145", 15), ("-0.001", 0), ("-0.005", -1), (" 7.5 ", 750),
    ("5.", 500), (".5", 50), ("+3.10", 310), ("0.999", 100), ("123456789.99", 12345678999),
    ("19.994", 1999), ("0.0049", 0),
])
def test_to_cents(t, c):
    r = to_cents(t)
    assert r == c and isinstance(r, int)

@pytest.mark.parametrize("bad", ["", " ", ".", "abc", "1.2.3", "1e3", "--1", "1,5", "+"])
def test_to_cents_invalid(bad):
    with pytest.raises(ValueError):
        to_cents(bad)

def test_allocate_thirds():
    assert allocate(100, [1, 1, 1]) == [34, 33, 33]

def test_allocate_largest_remainder_not_first():
    assert allocate(10, [3, 2, 1]) == [5, 3, 2]

def test_allocate_ties_lowest_index():
    assert allocate(2, [1, 1, 1]) == [1, 1, 0]
    assert allocate(1, [1, 1]) == [1, 0]

def test_allocate_zero_weight():
    assert allocate(7, [0, 1, 0, 1]) == [0, 4, 0, 3]
    assert allocate(5, [0, 5]) == [0, 5]

def test_allocate_zero_total():
    assert allocate(0, [1, 2]) == [0, 0]

def test_allocate_sum_invariant():
    for total in range(0, 40):
        for ws in ([1, 2, 3], [7, 7, 7, 7], [1, 100, 3], [5]):
            out = allocate(total, ws)
            assert sum(out) == total and len(out) == len(ws)
            assert all(isinstance(x, int) and x >= 0 for x in out)

def test_allocate_big():
    assert allocate(1000001, [1, 1, 1]) == [333334, 333334, 333333]

def test_allocate_proportional():
    assert allocate(99, [1, 2, 3]) == [17, 33, 49]

@pytest.mark.parametrize("total,w", [(-1, [1]), (5, []), (5, [0, 0]), (5, [1, -1])])
def test_allocate_invalid(total, w):
    with pytest.raises(ValueError):
        allocate(total, w)
