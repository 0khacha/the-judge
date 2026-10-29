import pytest

from exprlib.evaluator import evaluate, EvalError
from exprlib.errors import EvalError as ErrorsEvalError


def test_evalerror_is_same_class():
    assert EvalError is ErrorsEvalError


# normal cases
@pytest.mark.parametrize("text, expected", [
    ("1+2*3", 7),
    ("(1+2)*3", 9),
    ("2+3*4", 14),
    ("10-4-3", 3),
    ("8/4/2", 1),
    ("7/2", 3.5),
    ("1.5*2", 3.0),
    ("(2+3)*(4-1)", 15),
    ("(((1)))", 1),
    ("2*3+4", 10),
    ("10-2*3", 4),
])
def test_arithmetic(text, expected):
    assert evaluate(text) == expected


# exponentiation
@pytest.mark.parametrize("text, expected", [
    ("2**3**2", 512),
    ("-2**2", -4),
    ("2**-1", 0.5),
    ("2**-2**2", 0.0625),
    ("-2**-2", -0.25),
    ("(-2)**2", 4),
    ("-1 ** 2", -1),
    ("2**3*2", 16),
    ("2**(-1)", 0.5),
    ("4 ** 0.5", 2.0),
])
def test_exponentiation(text, expected):
    assert evaluate(text) == expected


# unary signs
@pytest.mark.parametrize("text, expected", [
    ("--3", 3),
    ("2 - -3", 5),
    ("+3", 3),
    ("+-+3", -3),
    ("2*-3", -6),
    ("-(2+3)", -5),
    ("- 4 + 1", -3),
])
def test_unary(text, expected):
    assert evaluate(text) == expected


# variables
def test_variables():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9
    assert evaluate("x", {"x": 5}) == 5
    assert evaluate("-x**2", {"x": 3}) == -9
    assert evaluate("2**x", {"x": 3}) == 8
    assert evaluate("x/2", {"x": 3}) == 1.5
    assert evaluate("x_1+1", {"x_1": 2}) == 3


def test_whitespace_is_ignored():
    assert evaluate("  1 + 2  ") == 3


# invalid input: every failure must be EvalError
@pytest.mark.parametrize("text", [
    "",
    "   ",
    "()",
    "(1+2",
    "1+2)",
    ")(",
    "1 +",
    "* 2",
    "**2",
    "2 **",
    "1 2",
    "(1) 2",
    "1.2.3",
    "1 @ 2",
    "1 % 2",
    "$",
    "1 / 0",
    "1/0.0",
    "1/(2-2)",
    "0 ** -1",
])
def test_invalid_raises_evalerror(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_undefined_variable_raises_evalerror():
    with pytest.raises(EvalError):
        evaluate("a + 1")
    with pytest.raises(EvalError):
        evaluate("a + 1", {"b": 2})
    with pytest.raises(EvalError):
        evaluate("x")


def test_none_variables_with_name_raises_evalerror():
    with pytest.raises(EvalError):
        evaluate("x", None)
