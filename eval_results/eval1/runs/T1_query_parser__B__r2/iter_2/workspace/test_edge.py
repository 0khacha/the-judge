from querystring import parse_query as p

def test_leading_q_and_empty():
    assert p("?a=1&&b=2&") == {"a": ["1"], "b": ["2"]}
    assert p("") == {} and p("?") == {}

def test_first_equals():
    assert p("a=b=c") == {"a": ["b=c"]}

def test_no_equals():
    assert p("flag&x=") == {"flag": [""], "x": [""]}

def test_percent():
    assert p("n=%C3%A9&m=a%2Bb&k%20x=1") == {"n": ["é"], "m": ["a+b"], "k x": ["1"]}

def test_invalid_escape():
    assert p("a=%zz&b=%4&c=100%") == {"a": ["%zz"], "b": ["%4"], "c": ["100%"]}

def test_order():
    assert list(p("b=1&a=2&b=3")) == ["b", "a"]
    assert p("b=1&a=2&b=3")["b"] == ["1", "3"]
