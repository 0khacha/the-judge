import pytest
from slug import slugify

def test_symbols():
    assert slugify("  !!a__b  ") == "a-b"
    assert slugify("!!!") == ""
    assert slugify("日本") == ""

def test_truncate_words():
    assert slugify("hello world foo", 11) == "hello-world"
    assert slugify("hello world foo", 12) == "hello-world"
    assert slugify("hello world foo", 15) == "hello-world-foo"
    assert slugify("hello world", 5) == "hello"
    assert slugify("hello world", 6) == "hello"

def test_long_first_word():
    assert slugify("abcdefgh ij", 4) == "abcd"

def test_bad_max():
    with pytest.raises(ValueError):
        slugify("a", 0)
