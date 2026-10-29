import pytest

from money import to_cents, allocate


# ---- to_cents: normal cases ----

def test_basic_values():
    assert to_cents("12.34") == 1234
    assert to_cents("5") == 500
    assert to_cents("-0.5") == -50
    assert to_cents("0") == 0
    assert to_cents("100.00") == 10000


def test_optional_plus_sign():
    assert to_cents("+3.10") == 310
    assert to_cents("+7") == 700


def test_surrounding_whitespace_allowed():
    assert to_cents("  12.34 ") == 1234
    assert to_cents("\t-1.5\n") == -150


def test_trailing_and_leading_dot_allowed():
    assert to_cents("5.") == 500
    assert to_cents(".5") == 50
    assert to_cents("-.5") == -50
    assert to_cents("+.25") == 25


def test_fewer_than_two_fraction_digits_are_padded():
    assert to_cents("1.2") == 120
    assert to_cents("0.07") == 7


# ---- to_cents: rounding (half up in magnitude) ----

def test_rounding_half_up_away_from_zero():
    assert to_cents("0.125") == 13
    assert to_cents("-0.125") == -13
    assert to_cents("0.135") == 14
    assert to_cents("-0.135") == -14


def test_rounding_down_below_half():
    assert to_cents("0.124") == 12
    assert to_cents("-0.124") == -12


def test_tiny_value_rounds_to_zero():
    assert to_cents("-0.001") == 0
    assert to_cents("0.004") == 0


def test_rounding_carries_into_integer_part():
    assert to_cents("9.995") == 1000
    assert to_cents("-9.995") == -1000
    assert to_cents("0.999") == 100


def test_large_values_exact_no_float_error():
    assert to_cents("12345678901234567890.99") == 1234567890123456789099
    assert to_cents("0.1") == 10


# ---- to_cents: invalid input ----

@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "+",
        "-",
        ".",
        "-.",
        "abc",
        "12a",
        "1.2.3",
        "1..2",
        "1e3",
        "1E3",
        "1.5e-2",
        "--1",
        "1-",
        "$5",
        "1,000",
    ],
)
def test_invalid_strings_raise(bad):
    with pytest.raises(ValueError):
        to_cents(bad)


@pytest.mark.parametrize("bad", [None, 12, 1.5, b"1.00", ["1.00"]])
def test_non_string_raises(bad):
    with pytest.raises(ValueError):
        to_cents(bad)


# ---- allocate: normal cases ----

def test_allocate_examples_from_visible_tests():
    assert allocate(100, [1, 1, 2]) == [25, 25, 50]
    assert allocate(10, [1, 1]) == [5, 5]


def test_allocate_largest_remainder_distributes_leftover():
    # 10 * [1,1,1] / 3 -> floors 3,3,3, remainder 1 each; leftover 1 goes to index 0
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]


def test_allocate_leftover_goes_to_largest_remainders():
    # total 10, weights [1,2,3] sum 6: floors 1,3,5 (sum 9); remainders 4,2,0 (mod 6)
    # leftover 1 goes to index 0 (largest remainder 4)
    assert allocate(10, [1, 2, 3]) == [2, 3, 5]


def test_allocate_tie_broken_by_lowest_index():
    assert allocate(1, [1, 1, 1]) == [1, 0, 0]
    assert allocate(2, [1, 1, 1]) == [1, 1, 0]


def test_allocate_zero_weight_gets_zero():
    # floors 0,3,0,3; remainders 0,1,0,1; leftover 1 goes to lowest index among ties (1)
    assert allocate(7, [0, 1, 0, 1]) == [0, 4, 0, 3]


def test_allocate_total_zero():
    assert allocate(0, [3, 5]) == [0, 0]


def test_allocate_single_weight_gets_everything():
    assert allocate(123, [9]) == [123]


def test_allocate_sum_always_equals_total():
    for total in range(0, 60):
        for weights in ([1, 2, 3], [5, 0, 7], [1, 1, 1, 1, 1], [3, 3], [10, 1]):
            shares = allocate(total, weights)
            assert sum(shares) == total
            assert len(shares) == len(weights)
            assert all(s >= 0 for s in shares)


def test_allocate_returns_list_of_ints():
    result = allocate(10, [1, 2])
    assert isinstance(result, list)
    assert all(type(x) is int for x in result)


def test_allocate_large_numbers_exact():
    total = 10**18 + 1
    weights = [1, 1, 1]
    shares = allocate(total, weights)
    assert sum(shares) == total
    assert max(shares) - min(shares) <= 1


# ---- allocate: invalid input ----

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
