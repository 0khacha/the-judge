import pytest
from wrap import wrap_text, display_width


# ---------- display_width ----------

def test_display_width_ascii_and_empty():
    assert display_width("") == 0
    assert display_width("abc") == 3


def test_display_width_wide_and_fullwidth():
    assert display_width("中") == 2
    assert display_width("中文") == 4
    assert display_width("Ａ") == 2  # fullwidth A (category F)


def test_display_width_zero_width():
    assert display_width("é") == 1  # e + combining acute (Mn)
    assert display_width("́") == 0
    assert display_width("​") == 0  # zero width space (Cf)
    assert display_width("a​b") == 2


def test_display_width_precomposed_is_one():
    assert display_width("é") == 1


# ---------- wrap_text: greedy fill ----------

def test_greedy_fill():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]


def test_blank_and_empty_return_empty_list():
    assert wrap_text("", 5) == []
    assert wrap_text("   \n\t ", 5) == []


def test_whitespace_is_collapsed():
    assert wrap_text("a   b", 5) == ["a b"]
    assert wrap_text("a\n\nb\tc", 10) == ["a b c"]


def test_word_exactly_width_is_not_split():
    assert wrap_text("abcd", 4) == ["abcd"]


def test_word_that_does_not_fit_starts_new_line():
    assert wrap_text("ab abcd", 4) == ["ab", "abcd"]


def test_line_fits_exactly():
    assert wrap_text("ab cd", 5) == ["ab cd"]
    assert wrap_text("ab cd", 4) == ["ab", "cd"]


# ---------- wrap_text: hard split ----------

def test_long_word_hard_split():
    assert wrap_text("abcdefgh", 3) == ["abc", "def", "gh"]


def test_final_piece_is_joinable():
    assert wrap_text("abcdefghij k", 4) == ["abcd", "efgh", "ij k"]


def test_final_piece_does_not_join_if_no_room():
    assert wrap_text("abcdefgh k", 4) == ["abcd", "efgh", "k"]


def test_long_word_after_text_starts_on_new_line():
    assert wrap_text("hi abcdef", 3) == ["hi", "abc", "def"]


def test_zero_width_stays_with_preceding_char():
    assert wrap_text("ab​cd", 2) == ["ab​", "cd"]


def test_zero_width_combining_not_separated():
    # "e" + combining acute repeated: each pair is width 1
    word = "é" * 3
    assert wrap_text(word, 2) == ["éé", "é"]


def test_single_wide_char_alone_on_line():
    assert wrap_text("中文", 1) == ["中", "文"]


def test_wide_chars_split_by_width():
    assert wrap_text("中文字", 4) == ["中文", "字"]


def test_wide_char_never_dropped():
    assert wrap_text("a中b", 1) == ["a", "中", "b"]


# ---------- wrap_text: errors ----------

@pytest.mark.parametrize("bad", [0, -1])
def test_width_below_one_raises(bad):
    with pytest.raises(ValueError):
        wrap_text("x", bad)


@pytest.mark.parametrize("bad", [1.5, "5", None])
def test_non_int_width_raises(bad):
    with pytest.raises(ValueError):
        wrap_text("x", bad)
