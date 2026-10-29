from exprlib.evaluator import evaluate, EvalError

def test_basic():
    assert evaluate("1+2*3") == 7
    assert evaluate("(1+2)*3") == 9

def test_vars():
    assert evaluate("x*2 + y", {"x": 4, "y": 1}) == 9

def test_error():
    try:
        evaluate("1 +")
    except EvalError:
        pass
    else:
        raise AssertionError("expected EvalError")
