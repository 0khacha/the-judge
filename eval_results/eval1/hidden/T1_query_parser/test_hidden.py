import pytest

from querystring import parse_query


@pytest.mark.parametrize("qs,expected", [
    ("a=1&b=2", {"a": ["1"], "b": ["2"]}),
    ("", {}),
    ("?", {}),
    ("?a=1", {"a": ["1"]}),
    ("a&b=", {"a": [""], "b": [""]}),
    ("a=b=c", {"a": ["b=c"]}),
    ("&&a=1&&", {"a": ["1"]}),
    ("%E2%9C%93=ok", {"\u2713": ["ok"]}),
    ("x=%zz", {"x": ["%zz"]}),
    ("x=%4", {"x": ["%4"]}),
    ("x=%2B1", {"x": ["+1"]}),
    ("+k+=+v+", {" k ": [" v "]}),
    ("caf%C3%A9=1", {"caf\u00e9": ["1"]}),
])
def test_cases(qs, expected):
    assert parse_query(qs) == expected


def test_key_order_is_first_seen():
    assert list(parse_query("b=1&a=2&b=3")) == ["b", "a"]
    assert parse_query("b=1&a=2&b=3")["b"] == ["1", "3"]
