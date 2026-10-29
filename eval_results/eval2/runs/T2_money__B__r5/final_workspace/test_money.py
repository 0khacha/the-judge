import pytest
from money import to_cents, allocate


# ---- to_cents: normal cases ----
def test_to_cents_basic():
    assert to_cents("12.34") == 1234
    assert to_cents("5") == 500
    assert to_cents("-0.5") == -50
    assert to_cents("0") == 0
    assert to_cents("100.00") == 10000


def test_to_cents_sign_and_bare_dots():
    assert to_cents("+1.5") == 150
    assert to_cents("5.") == 500
    assert to_cents(".5") == 50
    assert to_cents("-.25") == -25
    assert to_cents("+.7") == 70


def test_to_cents_whitespace():
    assert to_cents("  12.34  ") == 1234
    assert to_cents("\t-3\n") == -300


def test_to_cents_rounding_half_up_magnitude():
    assert to_cents("0.125") == 13
    assert to_cents("-0.125") == -13
    assert to_cents("0.124") == 12
    assert to_cents("0.126") == 13
    assert to_cents("-0.126") == -13
    assert to_cents("1.005") == 101
    assert to_cents("-1.005") == -101


def test_to_cents_tiny_values_round_to_zero():
    assert to_cents("-0.001") == 0
    assert to_cents("0.004") == 0
    assert to_cents("0.005") == 1
    assert to_cents("0.00000000000000000000001") == 0


def test_to_cents_large_values_exact():
    assert to_cents("12345678901234567890.99") == 1234567890123456789099
    assert to_cents("0.1") + to_cents("0.2") == 30


# ---- to_cents: invalid input ----
@pytest.mark.parametrize("bad", [
    "", "   ", "abc", "1a", "1.2.3", ".", "+", "-", "+-1", "--1",
    "1e3", "1E-2", "1,000", "$5", "1 2", "0x10", "inf", "nan",
])
def test_to_cents_invalid_strings_raise(bad):
    with pytest.raises(ValueError):
        to_cents(bad)


@pytest.mark.parametrize("bad", [None, 1, 1.5, 12, [1], b"1.5"])
def test_to_cents_non_string_raises(bad):
    with pytest.raises(ValueError):
        to_cents(bad)


# ---- allocate: normal cases ----
def test_allocate_basic():
    assert allocate(100, [1, 1, 2]) == [25, 25, 50]
    assert allocate(10, [1, 1]) == [5, 5]


def test_allocate_largest_remainder_handout():
    # 10 split 3 ways: floors 3,3,3 ; remainders all equal -> lowest index gets extra
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]
    # 5 split [1,1,1,1]: floors 1,1,1,1 ; leftover 1 -> index 0
    assert allocate(5, [1, 1, 1, 1]) == [2, 1, 1, 1]


def test_allocate_largest_fraction_wins():
    # total=10, weights=[1,2,2]: sum=5, exact = 2, 4, 4 -> no leftover
    assert allocate(10, [1, 2, 2]) == [2, 4, 4]
    # total=7, weights=[1,1,1]: exact 7/3 each -> floors 2,2,2 leftover 1 -> index 0
    assert allocate(7, [1, 1, 1]) == [3, 2, 2]
    # total=4, weights=[1,3]: exact 1, 3 -> exact
    assert allocate(4, [1, 3]) == [1, 3]
    # total=5, weights=[1,2]: exact 5/3=1.67, 10/3=3.33 -> floors 1,3, leftover to largest remainder (index 0 .67 vs index1 .33)
    assert allocate(5, [1, 2]) == [2, 3]


def test_allocate_zero_weight_gets_nothing():
    assert allocate(10, [0, 1, 1]) == [0, 5, 5]
    assert allocate(7, [1, 0, 0]) == [7, 0, 0]


def test_allocate_zero_total():
    assert allocate(0, [1, 2, 3]) == [0, 0, 0]


def test_allocate_single_weight():
    assert allocate(123, [5]) == [123]


def test_allocate_sums_to_total_and_nonnegative():
    import random
    rng = random.Random(42)
    for _ in range(300):
        total = rng.randint(0, 10000)
        n = rng.randint(1, 8)
        weights = [rng.randint(0, 50) for _ in range(n)]
        if sum(weights) == 0:
            weights[0] = 1
        out = allocate(total, weights)
        assert len(out) == n
        assert sum(out) == total
        assert all(isinstance(x, int) and x >= 0 for x in out)


def test_allocate_each_share_within_one_of_exact():
    import random
    rng = random.Random(7)
    for _ in range(200):
        total = rng.randint(0, 5000)
        weights = [rng.randint(0, 20) for _ in range(rng.randint(1, 6))]
        if sum(weights) == 0:
            weights[-1] = 3
        s = sum(weights)
        out = allocate(total, weights)
        for w, x in zip(weights, out):
            exact_floor = total * w // s
            assert exact_floor <= x <= exact_floor + 1


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
