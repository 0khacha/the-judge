import pytest
from slug import slugify


def test_punct_runs():
    assert slugify("  Hello,,, World!! ") == "hello-world"


def test_empty():
    assert slugify("!!!") == ""
    assert slugify("") == ""


def test_nonascii_removed():
    assert slugify("a中b") == "ab"


def test_max_length_whole_words():
    assert slugify("hello world foo", 11) == "hello-world"
    assert slugify("hello world foo", 12) == "hello-world"
    assert slugify("hello world foo", 15) == "hello-world-foo"


def test_max_length_first_word_cut():
    assert slugify("abcdefghij kl", 4) == "abcd"


def test_max_length_no_trailing_dash():
    assert not slugify("ab cd", 3).endswith("-")
    assert slugify("ab cd", 3) == "ab"


def test_invalid_max_length():
    with pytest.raises(ValueError):
        slugify("x", 0)
    with pytest.raises(ValueError):
        slugify("x", -1)
