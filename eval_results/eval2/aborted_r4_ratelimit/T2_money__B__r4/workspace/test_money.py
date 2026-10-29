import pytest

from money import allocate, to_cents


# ---- to_cents: normal cases ----

@pytest.mark.parametrize(
    "text, expected",
    [
        ("0", 0),
        ("1", 100),
        ("12.34", 1234),
        ("12.3", 1230),
        ("0.5", 50),
        ("+3.07", 307),
        ("-3.07", -307),
        ("5.", 500),
        (".5", 50),
        ("  42.10  ", 4210),
        ("-0", 0),
    ],
)
def test_to_cents_normal(text, expected):
    assert to_cents(text) == expected


def test_to_cents_returns_int():
    assert type(to_cents("1.5")) is int


# ---- to_cents: rounding (half up in magnitude) ----

@pytest.mark.parametrize(
    "text, expected",
    [
        ("0.125", 13),
        ("-0.125", -13),
        ("0.124", 12),
        ("-0.124", -12),
        ("0.126", 13),
        ("-0.001", 0),
        ("0.001", 0),
        ("0.995", 100),
        ("-0.995", -100),
        ("1.005", 101),
        ("2.675", 268),
    ],
)
def test_to_cents_rounding(text, expected):
    assert to_cents(text) == expected


def test_to_cents_no_float_error():
    # float("0.29") * 100 is 28.999... ; must still give 29
    assert to_cents("0.29") == 29
    assert to_cents("1.15") == 115


# ---- to_cents: invalid input ----

@pytest.mark.parametrize(
    "text",
    ["", "   ", ".", "-", "+", "abc", "1a", "1.2.3", "1e5", "1E3", "--1", "1,000", "0x10"],
)
def test_to_cents_invalid_text(text):
    with pytest.raises(ValueError):
        to_cents(text)


@pytest.mark.parametrize("value", [None, 1, 1.5, b"1.0", ["1"]])
def test_to_cents_non_string(value):
    with pytest.raises(ValueError):
        to_cents(value)


# ---- allocate: normal cases ----

def test_allocate_even_split():
    assert allocate(10, [1, 1]) == [5, 5]


def test_allocate_largest_remainder_example():
    # 10 * [1,1,1] / 3 -> 3.33 each, floors 3,3,3, one leftover to lowest index
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]


def test_allocate_proportional():
    assert allocate(100, [1, 2, 1]) == [25, 50, 25]


def test_allocate_remainder_goes_to_largest_fraction():
    # 10*[1,2]/3 -> 3.33, 6.67 ; floors 3,6 ; leftover 1 goes to index 1 (remainder .67)
    assert allocate(10, [1, 2]) == [3, 7]


def test_allocate_zero_weight_gets_nothing():
    assert allocate(10, [0, 1, 1]) == [0, 5, 5]


def test_allocate_total_zero():
    assert allocate(0, [1, 2, 3]) == [0, 0, 0]


def test_allocate_single_weight():
    assert allocate(7, [5]) == [7]


def test_allocate_sum_equals_total():
    weights = [3, 7, 11, 13]
    for total in range(0, 200):
        shares = allocate(total, weights)
        assert sum(shares) == total
        assert all(isinstance(s, int) for s in shares)


def test_allocate_tie_broken_by_lowest_index():
    # 1*[1,1,1,1]/4 ... total 2: each 0 rem 2 ; remainders equal -> indices 0 and 1 get one
    assert allocate(2, [1, 1, 1, 1]) == [1, 1, 0, 0]


def test_allocate_large_values_exact():
    total = 10**18 + 1
    weights = [1, 1, 1]
    shares = allocate(total, weights)
    assert sum(shares) == total
    assert max(shares) - min(shares) <= 1


# ---- allocate: invalid input ----

def test_allocate_negative_total():
    with pytest.raises(ValueError):
        allocate(-1, [1, 2])


def test_allocate_empty_weights():
    with pytest.raises(ValueError):
        allocate(10, [])


def test_allocate_negative_weight():
    with pytest.raises(ValueError):
        allocate(10, [1, -1, 2])


def test_allocate_all_zero_weights():
    with pytest.raises(ValueError):
        allocate(10, [0, 0])
