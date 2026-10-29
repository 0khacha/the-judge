import pytest
from wrap import wrap_text, display_width


def test_width_cjk():
    assert display_width("\u4f60\u597d") == 4
    assert display_width("a\u4f60") == 3
    assert display_width("\uff21") == 2      # fullwidth A

def test_width_combining():
    assert display_width("e\u0301") == 1
    assert display_width("\u200b") == 0      # zero width space (Cf)
    assert display_width("") == 0

def test_cjk_wrapping():
    assert wrap_text("\u4f60\u597d \u4e16\u754c", 5) == ["\u4f60\u597d", "\u4e16\u754c"]
    assert wrap_text("\u4f60\u597d \u4e16\u754c", 9) == ["\u4f60\u597d \u4e16\u754c"]

def test_cjk_hard_split_by_columns():
    assert wrap_text("\u4f60\u597d\u4e16\u754c\u4eba", 4) == ["\u4f60\u597d", "\u4e16\u754c", "\u4eba"]
    assert wrap_text("\u4f60\u597d\u4e16", 5) == ["\u4f60\u597d", "\u4e16"]

def test_combining_not_counted():
    word = "e\u0301" * 5
    assert wrap_text(word, 5) == [word]
    assert wrap_text("e\u0301e\u0301e\u0301", 2) == ["e\u0301e\u0301", "e\u0301"]

def test_mixed_line_fill():
    assert wrap_text("ab \u4f60\u597d cd", 7) == ["ab \u4f60\u597d", "cd"]
    assert wrap_text("ab \u4f60\u597d cd", 8) == ["ab \u4f60\u597d", "cd"]
    assert wrap_text("ab \u4f60\u597d cd", 10) == ["ab \u4f60\u597d cd"]

def test_long_ascii_word_split():
    assert wrap_text("abcdefghij", 4) == ["abcd", "efgh", "ij"]

def test_split_tail_joined_by_next_word():
    assert wrap_text("abcdefghij kl", 4) == ["abcd", "efgh", "ij", "kl"]
    assert wrap_text("abcdefghij k", 4) == ["abcd", "efgh", "ij k"]

def test_long_word_after_short():
    assert wrap_text("hi abcdefg", 5) == ["hi", "abcde", "fg"]

def test_exact_fit_and_boundary():
    assert wrap_text("abc def", 7) == ["abc def"]
    assert wrap_text("abc def", 6) == ["abc", "def"]
    assert wrap_text("a", 1) == ["a"]

def test_char_wider_than_width():
    assert wrap_text("\u4f60\u597d", 1) == ["\u4f60", "\u597d"]
    assert wrap_text("a\u4f60b", 1) == ["a", "\u4f60", "b"]

def test_unicode_whitespace_and_newlines():
    assert wrap_text("a\nb\t c", 10) == ["a b c"]
    assert wrap_text("a\u3000b", 10) == ["a b"]

def test_lines_within_width():
    text = "\u65e5\u672c\u8a9e\u306e\u30c6\u30ad\u30b9\u30c8 and some english words \u3068 more"
    for width in (4, 6, 9, 13):
        for line in wrap_text(text, width):
            assert display_width(line) <= width

@pytest.mark.parametrize("bad", [0, -3, 2.5, "5", None])
def test_bad_width(bad):
    with pytest.raises(ValueError):
        wrap_text("abc", bad)
