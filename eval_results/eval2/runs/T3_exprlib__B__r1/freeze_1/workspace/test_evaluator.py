import pytest

from exprlib.evaluator import evaluate, EvalError
from exprlib.errors import EvalError as ErrorsEvalError


# --- identity -------------------------------------------------------------

def test_eval_error_is_same_class():
    assert EvalError is ErrorsEvalError


# --- numbers and basic arithmetic ------------------------------------------

def test_single_number():
    assert evaluate("42") == 42
    assert evaluate("3.5") == 3.5


def test_addition_subtraction_left_assoc():
    assert evaluate("10 - 3 - 2") == 5
    assert evaluate("1 + 2 + 3") == 6


def test_multiplication_division_left_assoc():
    assert evaluate("8 / 4 / 2") == 1
    assert evaluate("2 * 3 * 4") == 24


def test_precedence_mul_over_add():
    assert evaluate("1+2*3") == 7
    assert evaluate("2*3+1") == 7
    assert evaluate("10-6/3") == 8


def test_parentheses():
    assert evaluate("(1+2)*3") == 9
    assert evaluate("((2))") == 2
    assert evaluate("2*(3+(4-1))") == 12


def test_true_division():
    assert evaluate("1/2") == 0.5
    assert evaluate("4/2") == 2.0
    assert isinstance(evaluate("4/2"), float)


def test_float_arithmetic():
    assert evaluate("1.5 * 2") == 3.0


def test_whitespace_is_ignored():
    assert evaluate("  1 +   2 ") == 3
    assert evaluate("\t(1+2)*3\n") == 9


# --- exponentiation --------------------------------------------------------

def test_power_basic():
    assert evaluate("2**3") == 8


def test_power_right_associative():
    assert evaluate("2**3**2") == 512


def test_power_binds_tighter_than_mul():
    assert evaluate("2*3**2") == 18


def test_power_negative_exponent():
    assert evaluate("2**-1") == 0.5


def test_power_exponent_with_plus_sign():
    assert evaluate("2**+3") == 8


def test_power_with_parenthesised_base():
    assert evaluate("(-2)**2") == 4


# --- unary operators -------------------------------------------------------

def test_unary_minus():
    assert evaluate("-5") == -5
    assert evaluate("-(2+3)") == -5


def test_unary_plus():
    assert evaluate("+5") == 5


def test_power_binds_tighter_than_unary_minus():
    assert evaluate("-2**2") == -4


def test_repeated_unary():
    assert evaluate("--3") == 3
    assert evaluate("-+-3") == 3


def test_binary_minus_with_unary_operand():
    assert evaluate("2 - -3") == 5
    assert evaluate("2--3") == 5


def test_unary_in_product():
    assert evaluate("3 * -2") == -6


# --- variables -------------------------------------------------------------

def test_variables():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9


def test_variable_alone():
    assert evaluate("abc", {"abc": 7}) == 7


def test_variable_underscore_and_digits():
    assert evaluate("_a1 + 1", {"_a1": 2}) == 3


def test_variable_with_power_and_unary():
    assert evaluate("-x**2", {"x": 3}) == -9


def test_variables_none_same_as_empty():
    assert evaluate("1+1", None) == 2


def test_variables_dict_not_mutated():
    env = {"x": 2}
    evaluate("x+1", env)
    assert env == {"x": 2}


# --- errors: every failure must be EvalError --------------------------------

@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_empty_input(text):
    with pytest.raises(EvalError):
        evaluate(text)


@pytest.mark.parametrize("text", ["(1+2", "1+2)", "((1)", "1))", ")(", "()"])
def test_unbalanced_or_empty_parens(text):
    with pytest.raises(EvalError):
        evaluate(text)


@pytest.mark.parametrize("text", ["1 +", "1 *", "1 -", "1 **", "1/", "-", "+", "*2"])
def test_dangling_or_leading_operator(text):
    with pytest.raises(EvalError):
        evaluate(text)


@pytest.mark.parametrize("text", ["1 2", "(1)(2)", "x y", "1 (2)", "2 3 4"])
def test_adjacent_operands(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_undefined_variable():
    with pytest.raises(EvalError):
        evaluate("x + 1", {"y": 2})


def test_undefined_variable_without_dict():
    with pytest.raises(EvalError):
        evaluate("x")


@pytest.mark.parametrize("text", ["1/0", "1/(2-2)", "5/0.0", "1 + 2/0"])
def test_division_by_zero(text):
    with pytest.raises(EvalError):
        evaluate(text)


@pytest.mark.parametrize("text", ["0**-1", "0 ** -1", "0.0**-2"])
def test_zero_to_negative_power(text):
    with pytest.raises(EvalError):
        evaluate(text)


@pytest.mark.parametrize("text", ["1 $ 2", "1 & 2", "a = 1", "1 % 2", "#", "1.2.3", "1."])
def test_illegal_characters(text):
    with pytest.raises(EvalError):
        evaluate(text)


def test_error_is_not_raw_python_exception():
    for text in ["", "1/0", "0**-1", "1 +", "$", "(", "q"]:
        try:
            evaluate(text)
        except EvalError:
            continue
        except Exception as exc:  # pragma: no cover - failure path
            raise AssertionError("%r raised %r" % (text, exc))
        raise AssertionError("%r did not raise" % text)
