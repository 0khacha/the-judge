import pytest

from exprlib.errors import EvalError as ErrorsEvalError
from exprlib.evaluator import EvalError, evaluate


def test_eval_error_is_same_class():
    assert EvalError is ErrorsEvalError


# ---- normal cases -------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("1", 1),
    ("42", 42),
    ("1.5", 1.5),
    ("1+2", 3),
    ("1-2", -1),
    ("2*3", 6),
    ("7/2", 3.5),
    ("1+2*3", 7),
    ("(1+2)*3", 9),
    ("10-4-3", 3),          # left-associative
    ("8/4/2", 1.0),         # left-associative, true division
    ("2*3+4*5", 26),
    ("((2))", 2),
])
def test_arithmetic(text, expected):
    assert evaluate(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("2**3", 8),
    ("2**3**2", 512),       # right-associative
    ("2**-1", 0.5),         # signed exponent
    ("2**+1", 2),
    ("-2**2", -4),          # ** binds tighter than unary minus
    ("(-2)**2", 4),
    ("2*3**2", 18),         # ** tighter than *
    ("2**3*2", 16),
])
def test_exponentiation(text, expected):
    assert evaluate(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("-3", -3),
    ("+3", 3),
    ("--3", 3),
    ("---3", -3),
    ("2 - -3", 5),
    ("2--3", 5),
    ("2+-3", -1),
    ("-(1+2)", -3),
    ("3*-2", -6),
])
def test_unary(text, expected):
    assert evaluate(text) == expected


def test_whitespace_is_ignored():
    assert evaluate("  1 +  2 * 3  ") == 7


# ---- variables ----------------------------------------------------------

def test_variables():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9


def test_variables_default_none():
    assert evaluate("1+1", None) == 2


def test_variable_used_twice_and_in_power():
    assert evaluate("x**2 + x", {"x": 3}) == 12


def test_undefined_variable_raises():
    with pytest.raises(EvalError):
        evaluate("x + 1")


def test_function_call_syntax_raises():
    with pytest.raises(EvalError):
        evaluate("f(1)")


# ---- invalid input: must raise EvalError --------------------------------

@pytest.mark.parametrize("text", [
    "",
    "   ",
    "(1+2",          # unbalanced open
    "1+2)",          # unbalanced close
    "()",
    "1 +",           # dangling operator
    "* 2",
    "1 2",           # two adjacent operands
    "(1)(2)",
    "1 @ 2",         # illegal character
    "1 & 2",
    "2***3",
    "1 +* 2",
    "1..2",
    "1.",
    "x y",
])
def test_invalid_syntax_raises(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_division_by_zero_raises():
    with pytest.raises(EvalError):
        evaluate("1/0")


def test_division_by_zero_float_raises():
    with pytest.raises(EvalError):
        evaluate("1.5/(2-2)")


def test_zero_to_negative_power_raises():
    with pytest.raises(EvalError):
        evaluate("0 ** -1")


def test_zero_float_to_negative_power_raises():
    with pytest.raises(EvalError):
        evaluate("0.0**-2")


def test_float_overflow_raises_eval_error():
    with pytest.raises(EvalError):
        evaluate("10.0**400")


def test_huge_int_float_overflow_raises_eval_error():
    with pytest.raises(EvalError):
        evaluate("10**400 * 1.0")


def test_error_is_eval_error_not_raw_exception():
    for text in ["", "1/0", "1 +", "x", "1 @ 2", "(", "0**-1"]:
        try:
            evaluate(text)
        except EvalError:
            continue
        except Exception as exc:  # pragma: no cover - failure path
            raise AssertionError("raw %r for %r" % (exc, text))
        raise AssertionError("expected EvalError for %r" % text)
