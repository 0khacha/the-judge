import pytest
from slug import slugify

def test_empty():
    assert slugify("!!!") == ""
    assert slugify("  a   b  ") == "a-b"

def test_unicode_drop():
    assert slugify("a\u4e2db") == "a-b" or slugify("a\u4e2db") == "ab"
    assert slugify("Ünï") == "uni"

def test_max_words():
    assert slugify("hello world foo", 11) == "hello-world"
    assert slugify("hello world foo", 12) == "hello-world"
    assert slugify("hello world foo", 14) == "hello-world"
    assert slugify("hello world foo", 15) == "hello-world-foo"
    assert slugify("hello world", 8) == "hello"

def test_long_first_word():
    assert slugify("abcdefghij kl", 4) == "abcd"

def test_invalid():
    with pytest.raises(ValueError):
        slugify("a", 0)
