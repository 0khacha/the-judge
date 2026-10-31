from querystring import parse_query


def test_leading_question_mark():
    assert parse_query("?a=1") == {"a": ["1"]}
    assert parse_query("??a=1") == {"?a": ["1"]}


def test_empty_segments():
    assert parse_query("a=1&&b=2&") == {"a": ["1"], "b": ["2"]}
    assert parse_query("") == {}


def test_first_equals_split_and_no_equals():
    assert parse_query("a=b=c") == {"a": ["b=c"]}
    assert parse_query("flag") == {"flag": [""]}


def test_percent_decoding():
    assert parse_query("a=%41%20b") == {"a": ["A b"]}
    assert parse_query("c=%E2%82%AC") == {"c": ["€"]}
    assert parse_query("%6B=v") == {"k": ["v"]}


def test_invalid_escapes_literal():
    assert parse_query("a=%zz&b=%4") == {"a": ["%zz"], "b": ["%4"]}


def test_order():
    assert list(parse_query("b=1&a=2&b=3")) == ["b", "a"]
    assert parse_query("b=1&a=2&b=3")["b"] == ["1", "3"]
