import pytest

from money import to_cents, allocate


# ---------- to_cents: normal cases ----------

@pytest.mark.parametrize("text, expected", [
    ("12.34", 1234),
    ("5", 500),
    ("-0.5", -50),
    ("+3", 300),
    ("0", 0),
    ("-0", 0),
    ("+.25", 25),
    ("5.", 500),
    (".5", 50),
    ("0.10", 10),
    ("-12.00", -1200),
])
def test_to_cents_basic(text, expected):
    assert to_cents(text) == expected


def test_to_cents_surrounding_whitespace():
    assert to_cents("  7.1 ") == 710
    assert to_cents("\t-2.05\n") == -205


# ---------- to_cents: rounding (half up in magnitude) ----------

@pytest.mark.parametrize("text, expected", [
    ("0.125", 13),
    ("-0.125", -13),
    ("0.124", 12),
    ("-0.001", 0),
    ("0.001", 0),
    ("0.005", 1),
    ("1.005", 101),
    ("2.675", 268),
    ("0.1249", 12),
    ("-0.999", -100),
])
def test_to_cents_rounding(text, expected):
    assert to_cents(text) == expected


def test_to_cents_large_value_is_exact():
    assert to_cents("12345678901234567890.99") == 1234567890123456789099


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
    "$5",
    "12a",
])
def test_to_cents_invalid_string_raises(text):
    with pytest.raises(ValueError):
        to_cents(text)


@pytest.mark.parametrize("value", [None, 5, 1.5, 12, ["1.00"]])
def test_to_cents_non_string_raises(value):
    with pytest.raises(ValueError):
        to_cents(value)


# ---------- allocate: normal cases ----------

def test_allocate_spec_examples():
    assert allocate(100, [1, 1, 2]) == [25, 25, 50]
    assert allocate(10, [1, 1]) == [5, 5]


def test_allocate_single_weight_gets_everything():
    assert allocate(100, [1]) == [100]


def test_allocate_zero_total():
    assert allocate(0, [1, 2]) == [0, 0]


def test_allocate_zero_weight_gets_nothing():
    assert allocate(7, [0, 1]) == [0, 7]
    assert allocate(5, [3, 0, 2]) == [3, 0, 2]


def test_allocate_leftover_goes_to_largest_remainder():
    # 1*1/6 -> rem 1, 2/6 -> rem 2, 3/6 -> rem 3: leftover cent goes to index 2
    assert allocate(1, [1, 2, 3]) == [0, 0, 1]


def test_allocate_ties_broken_by_lowest_index():
    # 10/3 each: floor 3, one leftover, all remainders equal -> lowest index wins
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]


def test_allocate_always_sums_to_total():
    cases = [
        (1000, [3, 7, 11]),
        (99, [1, 1, 1, 1, 1]),
        (1, [5, 5, 5]),
        (12345, [2, 0, 9, 4]),
    ]
    for total, weights in cases:
        shares = allocate(total, weights)
        assert sum(shares) == total
        assert len(shares) == len(weights)
        assert all(isinstance(s, int) and s >= 0 for s in shares)


def test_allocate_is_exact_for_large_values():
    total = 10**18 + 1
    shares = allocate(total, [1, 2, 3])
    assert sum(shares) == total
    assert shares == [166666666666666667, 333333333333333334, 500000000000000000]


# ---------- allocate: invalid input ----------

def test_allocate_negative_total_raises():
    with pytest.raises(ValueError):
        allocate(-1, [1, 2])


def test_allocate_empty_weights_raises():
    with pytest.raises(ValueError):
        allocate(10, [])


def test_allocate_negative_weight_raises():
    with pytest.raises(ValueError):
        allocate(10, [1, -1])


def test_allocate_all_zero_weights_raises():
    with pytest.raises(ValueError):
        allocate(10, [0, 0])
