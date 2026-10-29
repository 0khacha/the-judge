import pytest
from wrap import wrap_text, display_width

def test_basic():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]

def test_empty_and_collapse():
    assert wrap_text("   ", 5) == []
    assert wrap_text("a   b", 5) == ["a b"]

def test_width_and_errors():
    assert display_width("abc") == 3
    with pytest.raises(ValueError):
        wrap_text("x", 0)
