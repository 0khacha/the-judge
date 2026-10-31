import pytest

from slug import slugify


@pytest.mark.parametrize("text,expected", [
    ("Hello World", "hello-world"),
    ("", ""),
    ("!!!", ""),
    ("  --Hello--  ", "hello"),
    ("\u00c5ngstr\u00f6m", "angstrom"),
    ("\u65e5\u672c\u8a9e text", "text"),
    ("a_b", "a-b"),
    ("Version 2.0", "version-2-0"),
    ("\ufb01ne", "fine"),
    ("A  &  B", "a-b"),
])
def test_slugify(text, expected):
    assert slugify(text) == expected


@pytest.mark.parametrize("text,n,expected", [
    ("hello world foo", 11, "hello-world"),
    ("hello world foo", 12, "hello-world"),
    ("hello world", 5, "hello"),
    ("hello world", 7, "hello"),
    ("supercalifragilistic", 5, "super"),
    ("a b", 2, "a"),
    ("a b", 3, "a-b"),
    ("hello", 100, "hello"),
])
def test_max_length(text, n, expected):
    result = slugify(text, n)
    assert result == expected
    assert len(result) <= n and not result.endswith("-")


@pytest.mark.parametrize("n", [0, -1])
def test_invalid_max_length(n):
    with pytest.raises(ValueError):
        slugify("abc", n)
