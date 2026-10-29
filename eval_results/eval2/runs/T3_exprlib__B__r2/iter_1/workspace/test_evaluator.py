import pytest

from exprlib.evaluator import evaluate, EvalError
from exprlib import errors


def test_eval_error_is_same_class():
    assert EvalError is errors.EvalError


# --- normal cases -----------------------------------------------------------

def test_numbers_and_basic_ops():
    assert evaluate("1+2") == 3
    assert evaluate("7-10") == -3
    assert evaluate("6*7") == 42
    assert evaluate("7/2") == 3.5


def test_float_literals():
    assert evaluate("1.5*2") == 3.0
    assert evaluate("0.25+0.25") == 0.5


def test_true_division_returns_float_value():
    assert evaluate("1/2") == 0.5
    assert evaluate("8/4") == 2


def test_precedence_mul_over_add():
    assert evaluate("1+2*3") == 7
    assert evaluate("2*3+1") == 7
    assert evaluate("1+2*3**2") == 19


def test_parentheses():
    assert evaluate("(1+2)*3") == 9
    assert evaluate("((4))") == 4
    assert evaluate("(1+2)**2") == 9


def test_left_associative_sub_and_div():
    assert evaluate("10-4-3") == 3
    assert evaluate("8/4/2") == 1
    assert evaluate("2*3/4") == 1.5


def test_variables():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9
    assert evaluate("x", {"x": 0}) == 0
    assert evaluate("a_1 + b2", {"a_1": 1, "b2": 2}) == 3


def test_variables_none_is_empty():
    assert evaluate("1+1", None) == 2
    assert evaluate("1+1") == 2


def test_whitespace_is_ignored():
    assert evaluate("  1 +  2 * 3  ") == 7


# --- exponentiation ---------------------------------------------------------

def test_power_basic():
    assert evaluate("2**3") == 8
    assert evaluate("2 ** 10") == 1024


def test_power_is_right_associative():
    assert evaluate("2**3**2") == 512


def test_power_binds_tighter_than_mul():
    assert evaluate("3*2**2") == 12
    assert evaluate("2**2*3") == 12


def test_power_with_negative_exponent():
    assert evaluate("2**-1") == 0.5


def test_power_with_variables():
    assert evaluate("x**y", {"x": 3, "y": 2}) == 9


def test_unary_minus_looser_than_power():
    assert evaluate("-2**2") == -4
    assert evaluate("(-2)**2") == 4


def test_power_exponent_with_unary_and_right_assoc():
    assert evaluate("2**-1**2") == 0.5


def test_zero_power_zero_is_one():
    assert evaluate("0**0") == 1


# --- unary operators --------------------------------------------------------

def test_unary_plus():
    assert evaluate("+3") == 3
    assert evaluate("+(2+3)") == 5


def test_unary_minus():
    assert evaluate("-3") == -3
    assert evaluate("-(2+3)") == -5


def test_repeated_unary():
    assert evaluate("--3") == 3
    assert evaluate("- - 3") == 3


def test_binary_minus_followed_by_unary():
    assert evaluate("2 - -3") == 5
    assert evaluate("2*-3") == -6
    assert evaluate("2+-3") == -1


def test_unary_with_variables():
    assert evaluate("-x + 1", {"x": 5}) == -4


# --- invalid input must raise EvalError -------------------------------------

@pytest.mark.parametrize("text", [
    "",
    "   ",
    "(",
    ")",
    "()",
    "(1",
    "1)",
    "((1)",
    "1 +",
    "+",
    "*2",
    "1 *",
    "1 2",
    "x y",
    "(1)(2)",
    "1 +* 2",
    "1 % 2",
    "1 & 2",
    "1 ^ 2",
    "1 // 2",
    "1e5",
    "1.5.5",
    "@",
    "1 == 2",
])
def test_invalid_syntax_raises_eval_error(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_undefined_variable_raises_eval_error():
    with pytest.raises(EvalError):
        evaluate("x + 1")
    with pytest.raises(EvalError):
        evaluate("x + 1", {})
    with pytest.raises(EvalError):
        evaluate("x + 1", {"y": 1})


def test_function_call_is_not_supported():
    with pytest.raises(EvalError):
        evaluate("f(1)")


@pytest.mark.parametrize("text", [
    "1/0",
    "1/(2-2)",
    "1.0/0",
    "0 ** -1",
    "0.0 ** -1",
    "0**-2",
])
def test_division_by_zero_raises_eval_error(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_overflow_raises_eval_error():
    with pytest.raises(EvalError):
        evaluate("10.0 ** 1000")


def test_complex_result_raises_eval_error():
    with pytest.raises(EvalError):
        evaluate("(-8) ** 0.5")


def test_only_eval_error_escapes_for_bad_input():
    for text in ["", "1 +", "(", "1 2", "1/0", "q", "1 % 2", "0**-1"]:
        try:
            evaluate(text)
        except EvalError:
            pass
        else:
            raise AssertionError("expected EvalError for %r" % text)
