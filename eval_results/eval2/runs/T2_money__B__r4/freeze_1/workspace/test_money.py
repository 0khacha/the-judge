import pytest

from money import to_cents, allocate


# ---------- to_cents: normal cases ----------

def test_to_cents_basic():
    assert to_cents("12.34") == 1234
    assert to_cents("5") == 500
    assert to_cents("-0.5") == -50


def test_to_cents_plus_sign():
    assert to_cents("+3.10") == 310
    assert to_cents("+7") == 700


def test_to_cents_trailing_and_leading_dot():
    assert to_cents("5.") == 500
    assert to_cents(".5") == 50
    assert to_cents("-.5") == -50


def test_to_cents_whitespace():
    assert to_cents("  12.34  ") == 1234
    assert to_cents("\t-1.00\n") == -100


def test_to_cents_zero():
    assert to_cents("0") == 0
    assert to_cents("-0") == 0
    assert to_cents("0.00") == 0


def test_to_cents_large_value_no_float_error():
    assert to_cents("12345678901234567890.99") == 1234567890123456789099


# ---------- to_cents: rounding ----------

def test_to_cents_round_half_up_positive():
    assert to_cents("0.125") == 13


def test_to_cents_round_half_up_negative_away_from_zero():
    assert to_cents("-0.125") == -13


def test_to_cents_round_down_below_half():
    assert to_cents("0.124") == 12
    assert to_cents("-0.124") == -12


def test_to_cents_tiny_rounds_to_zero():
    assert to_cents("-0.001") == 0
    assert to_cents("0.001") == 0


def test_to_cents_rounding_carries():
    assert to_cents("0.995") == 100
    assert to_cents("9.999") == 1000
    assert to_cents("-9.995") == -1000


def test_to_cents_many_fraction_digits():
    assert to_cents("1.2500000") == 125
    assert to_cents("1.2549999999") == 125


# ---------- to_cents: invalid input ----------

@pytest.mark.parametrize("text", [
    "",
    "   ",
    ".",
    "+",
    "-",
    "-.",
    "abc",
    "12a",
    "1.2.3",
    "1e3",
    "1E3",
    "1,000",
    "$5",
    "--5",
    "+-5",
    "5 5",
    "nan",
    "inf",
])
def test_to_cents_invalid_text_raises(text):
    with pytest.raises(ValueError):
        to_cents(text)


@pytest.mark.parametrize("value", [None, 5, 1.5, b"5.00", ["5"]])
def test_to_cents_non_string_raises(value):
    with pytest.raises(ValueError):
        to_cents(value)


# ---------- allocate: normal cases ----------

def test_allocate_basic():
    assert allocate(100, [1, 1, 2]) == [25, 25, 50]
    assert allocate(10, [1, 1]) == [5, 5]


def test_allocate_largest_remainder_handout():
    # 10 * [1,1,1] / 3 -> floors 3,3,3, remainder 1 goes to index 0 (tie)
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]


def test_allocate_largest_remainder_not_lowest_index():
    # 10 * [1,2,2] / 5 -> exact 2,4,4 (no remainder)
    assert allocate(10, [1, 2, 2]) == [2, 4, 4]
    # 7 * [1,1,3] / 5 -> floors 1,1,4 (sum 6), remainders 2,2,1 -> leftover 1
    # goes to index 0 (tie with index 1, lowest index wins)
    assert allocate(7, [1, 1, 3]) == [2, 1, 4]


def test_allocate_remainder_picks_largest_fraction():
    # total=8, weights [1,1,1,1,1,1,0]... use simpler: total=5, weights [1,1,1]
    # floors 1,1,1 remainder 2 -> indices 0 and 1 (ties, lowest first)
    assert allocate(5, [1, 1, 1]) == [2, 2, 1]
    # total=4, weights [3,1]: exact 3,1 -> no remainder
    assert allocate(4, [3, 1]) == [3, 1]
    # total=10, weights [1,3,6]: exact 1,3,6
    assert allocate(10, [1, 3, 6]) == [1, 3, 6]
    # total=1, weights [1,2,2]: 1*1/5=0.2, 1*2/5=0.4, 0.4 -> leftover 1 to index 1
    assert allocate(1, [1, 2, 2]) == [0, 1, 0]


def test_allocate_zero_total():
    assert allocate(0, [1, 2, 3]) == [0, 0, 0]


def test_allocate_zero_weight_entries_get_nothing():
    assert allocate(10, [0, 1, 0, 1]) == [0, 5, 0, 5]


def test_allocate_single_weight():
    assert allocate(42, [7]) == [42]


def test_allocate_sum_always_equals_total():
    import random
    rng = random.Random(1234)
    for _ in range(300):
        total = rng.randint(0, 10_000)
        n = rng.randint(1, 8)
        weights = [rng.randint(0, 20) for _ in range(n)]
        if sum(weights) == 0:
            weights[0] = 1
        result = allocate(total, weights)
        assert sum(result) == total
        assert len(result) == n
        assert all(isinstance(x, int) and x >= 0 for x in result)


def test_allocate_large_values():
    total = 10**18 + 1
    weights = [1, 1, 1]
    result = allocate(total, weights)
    assert sum(result) == total
    assert max(result) - min(result) <= 1


# ---------- allocate: invalid input ----------

def test_allocate_negative_total_raises():
    with pytest.raises(ValueError):
        allocate(-1, [1, 2])


def test_allocate_empty_weights_raises():
    with pytest.raises(ValueError):
        allocate(10, [])


def test_allocate_negative_weight_raises():
    with pytest.raises(ValueError):
        allocate(10, [1, -1, 2])


def test_allocate_all_zero_weights_raises():
    with pytest.raises(ValueError):
        allocate(10, [0, 0])
