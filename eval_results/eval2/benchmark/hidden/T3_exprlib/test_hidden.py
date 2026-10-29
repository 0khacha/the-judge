import pytest
from exprlib.evaluator import evaluate, EvalError
import exprlib.errors


def test_same_class():
    assert EvalError is exprlib.errors.EvalError

def test_pow_right_assoc():
    assert evaluate("2**3**2") == 512

def test_unary_vs_pow():
    assert evaluate("-2**2") == -4
    assert evaluate("-x**2", {"x": 3}) == -9

def test_pow_negative_exp():
    assert evaluate("2**-1") == 0.5
    assert evaluate("2**-2**2") == 2 ** -(2 ** 2)

def test_double_unary():
    assert evaluate("--3") == 3
    assert evaluate("2 - -3") == 5
    assert evaluate("+-+4") == -4

def test_left_assoc():
    assert evaluate("2-3-4") == -5
    assert evaluate("8/4/2") == 1

def test_precedence_mix():
    assert evaluate("2+3*4**2/8") == 8
    assert evaluate("(2+3)*-2") == -10
    assert evaluate("-(1+2)**2") == -9
    assert evaluate("(-2)**2") == 4

def test_floats():
    assert evaluate("1.5*2") == 3.0
    assert evaluate("7/2") == 3.5

def test_vars():
    assert evaluate("a+b*c", {"a": 1, "b": 2, "c": 3}) == 7

@pytest.mark.parametrize("expr", ["", "   ", "1 +", "(1", "1)", "1 2", "* 3", "1 ** ", "()", "2 $ 3", "1 + * 2", "x"])
def test_errors(expr):
    with pytest.raises(EvalError):
        evaluate(expr)

def test_undefined_var():
    with pytest.raises(EvalError):
        evaluate("a + 1", {"b": 2})

def test_div_zero():
    with pytest.raises(EvalError):
        evaluate("1/0")
    with pytest.raises(EvalError):
        evaluate("1/(2-2)")
    with pytest.raises(EvalError):
        evaluate("0 ** -1")
