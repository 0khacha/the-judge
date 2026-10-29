import random

import pytest

from money import to_cents, allocate


# ---------- to_cents: normal cases ----------

@pytest.mark.parametrize("text, cents", [
    ("+1.5", 150),
    ("-1.5", -150),
    ("0", 0),
    ("-0", 0),
    ("  1.2  ", 120),
    ("5.", 500),
    (".5", 50),
    ("0.1", 10),
    ("0.01", 1),
    ("123456789012345678901234567890.99", 12345678901234567890123456789099),
])
def test_to_cents_normal(text, cents):
    assert to_cents(text) == cents


def test_to_cents_returns_int():
    assert type(to_cents("1.20")) is int


# ---------- to_cents: rounding (half up in magnitude) ----------

@pytest.mark.parametrize("text, cents", [
    ("0.125", 13),
    ("-0.125", -13),
    ("0.124", 12),
    ("-0.124", -12),
    ("-0.001", 0),
    ("0.001", 0),
    ("1.005", 101),
    ("-1.005", -101),
    ("1.999", 200),
    ("0.995", 100),
    ("0.2000", 20),
    ("+0.125", 13),
])
def test_to_cents_rounding(text, cents):
    assert to_cents(text) == cents


# ---------- to_cents: invalid input ----------

@pytest.mark.parametrize("text", [
    "",
    "   ",
    "abc",
    "1.2.3",
    "1e5",
    "1E5",
    "-",
    "+",
    ".",
    "-.",
    "1,000",
    "1 2",
    "--1",
    "+-1",
    "12a",
    "$5",
    "1_000",
])
def test_to_cents_invalid_string(text):
    with pytest.raises(ValueError):
        to_cents(text)


@pytest.mark.parametrize("value", [None, 5, 1.5, [1], b"1.5"])
def test_to_cents_non_string_raises(value):
    with pytest.raises(ValueError):
        to_cents(value)


# ---------- allocate: normal cases ----------

def test_allocate_largest_remainder_example():
    # 5 * [1,2] / 3 -> floors [1,3], remainder 1 goes to index 0 (rem 2 > 1)
    assert allocate(5, [1, 2]) == [2, 3]


def test_allocate_tie_goes_to_lowest_index():
    # 10 / 3 each: floors 3,3,3 and remainders all 1, leftover 1 -> index 0
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]


def test_allocate_single_cent_tie():
    assert allocate(1, [1, 1]) == [1, 0]


def test_allocate_zero_total():
    assert allocate(0, [1, 2]) == [0, 0]


def test_allocate_zero_weight_gets_nothing():
    assert allocate(10, [0, 1]) == [0, 10]


def test_allocate_single_weight():
    assert allocate(77, [5]) == [77]


def test_allocate_returns_ints_in_list():
    result = allocate(7, [1, 2])
    assert isinstance(result, list)
    assert all(type(x) is int for x in result)


def test_allocate_large_values_exact():
    total = 10**18 + 1
    weights = [3, 7, 11]
    result = allocate(total, weights)
    assert sum(result) == total
    assert all(r >= 0 for r in result)


def test_allocate_random_properties():
    rng = random.Random(12345)
    for _ in range(500):
        n = rng.randint(1, 6)
        weights = [rng.randint(0, 20) for _ in range(n)]
        if sum(weights) == 0:
            weights[rng.randrange(n)] = 1
        total = rng.randint(0, 10000)
        result = allocate(total, weights)
        s = sum(weights)
        assert sum(result) == total
        assert len(result) == n
        for w, share in zip(weights, result):
            floor_share = total * w // s
            assert share in (floor_share, floor_share + 1)
            if w == 0:
                assert share == 0


# ---------- allocate: invalid input ----------

def test_allocate_negative_total_raises():
    with pytest.raises(ValueError):
        allocate(-1, [1])


def test_allocate_empty_weights_raises():
    with pytest.raises(ValueError):
        allocate(5, [])


def test_allocate_negative_weight_raises():
    with pytest.raises(ValueError):
        allocate(5, [1, -1])


def test_allocate_all_zero_weights_raises():
    with pytest.raises(ValueError):
        allocate(5, [0, 0])
