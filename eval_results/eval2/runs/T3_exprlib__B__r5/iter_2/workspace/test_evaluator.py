import pytest

from exprlib.errors import EvalError as ErrorsEvalError
from exprlib.evaluator import EvalError, evaluate


def test_eval_error_is_same_class():
    assert EvalError is ErrorsEvalError


# Normal cases
@pytest.mark.parametrize(
    "text, expected",
    [
        ("1", 1),
        ("42", 42),
        ("1.5", 1.5),
        ("1 + 2", 3),
        ("1+2*3", 7),
        ("(1+2)*3", 9),
        ("10 - 4 - 3", 3),
        ("8 / 2 / 2", 2.0),
        ("1 / 2", 0.5),
        ("7 / 2", 3.5),
        ("2 * 3 + 4 * 5", 26),
        ("2 ** 3", 8),
        ("2**3**2", 512),
        ("2 ** 0.5", 2 ** 0.5),
        ("((2))", 2),
        ("  3 *  ( 4 + 1 )  ", 15),
    ],
)
def test_normal_cases(text, expected):
    assert evaluate(text) == expected


# Unary operators and precedence of exponentiation
@pytest.mark.parametrize(
    "text, expected",
    [
        ("-2**2", -4),
        ("-3", -3),
        ("+3", 3),
        ("--3", 3),
        ("2 - -3", 5),
        ("2**-1", 0.5),
        ("(-2)**2", 4),
        ("2*-3", -6),
        ("-(1+2)", -3),
        ("+-+-4", 4),
    ],
)
def test_unary_and_power(text, expected):
    assert evaluate(text) == expected


# Variables
def test_variables():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9
    assert evaluate("x", {"x": 2.5}) == 2.5
    assert evaluate("_a1 * 2", {"_a1": 3}) == 6


def test_variables_default_none():
    assert evaluate("1 + 1", None) == 2
    assert evaluate("1 + 1") == 2


def test_variable_lookup_is_by_name_only():
    assert evaluate("abc", {"abc": 0}) == 0


# Error cases: every failure must raise EvalError
@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "1 +",
        "+",
        "*2",
        "1 2",
        "(1",
        "1)",
        "()",
        "(1))",
        "1 $ 2",
        "1 & 2",
        "1 // 2",
        "2 ** ",
        "1 +* 2",
        "y",
        "x + 1",
    ],
)
def test_invalid_input_raises_eval_error(text):
    with pytest.raises(EvalError):
        evaluate(text)


@pytest.mark.parametrize("text", ["1 / 0", "1 / (2 - 2)", "0 ** -1", "0.0 ** -1", "0 / 0"])
def test_division_by_zero_raises_eval_error(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_undefined_variable_raises_eval_error():
    with pytest.raises(EvalError):
        evaluate("x + 1", {"y": 2})


def test_overflow_raises_eval_error_not_raw_exception():
    with pytest.raises(EvalError):
        evaluate("10.0 ** 400")


def test_deep_nesting_raises_eval_error():
    text = "(" * 5000 + "1" + ")" * 5000
    with pytest.raises(EvalError):
        evaluate(text)


def test_eval_error_is_exception_subclass():
    assert issubclass(EvalError, Exception)
