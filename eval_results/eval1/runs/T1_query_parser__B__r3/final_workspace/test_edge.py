from querystring import parse_query


def test_leading_question_mark():
    assert parse_query("?a=1") == {"a": ["1"]}
    assert parse_query("??a=1") == {"?a": ["1"]}


def test_empty_segments():
    assert parse_query("&&a=1&&") == {"a": ["1"]}
    assert parse_query("") == {}


def test_no_equals_and_first_equals():
    assert parse_query("a&b=") == {"a": [""], "b": [""]}
    assert parse_query("a=b=c") == {"a": ["b=c"]}


def test_percent_decoding():
    assert parse_query("a=%C3%A9") == {"a": ["\u00e9"]}
    assert parse_query("%6Bey=v%20x") == {"key": ["v x"]}
    assert parse_query("a=%2B") == {"a": ["+"]}


def test_invalid_escapes_literal():
    assert parse_query("a=%zz") == {"a": ["%zz"]}
    assert parse_query("a=%4") == {"a": ["%4"]}
    assert parse_query("a=%") == {"a": ["%"]}


def test_order():
    assert list(parse_query("b=1&a=2&b=3")) == ["b", "a"]
    assert parse_query("b=1&a=2&b=3")["b"] == ["1", "3"]
