import pytest

from wrap import display_width, wrap_text


# ---------- display_width ----------

def test_width_ascii():
    assert display_width("") == 0
    assert display_width("abc") == 3


def test_width_wide_and_fullwidth():
    assert display_width("中") == 2
    assert display_width("中文") == 4
    assert display_width("Ａ") == 2  # fullwidth A (F)


def test_width_combining_and_format_are_zero():
    assert display_width("é") == 1  # e + combining acute
    assert display_width("​") == 0  # zero-width space (Cf)
    assert display_width("a​b") == 2


def test_width_precomposed_is_one():
    assert display_width("é") == 1


# ---------- wrap_text: normal cases ----------

def test_basic_greedy():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]


def test_exact_fit_stays_on_line():
    assert wrap_text("abc de", 6) == ["abc de"]


def test_greedy_breaks_when_next_word_does_not_fit():
    assert wrap_text("aa bb cc", 5) == ["aa bb", "cc"]


def test_whitespace_collapsed_and_split():
    assert wrap_text("a   b\n\tc", 5) == ["a b c"]


def test_empty_and_blank_return_empty_list():
    assert wrap_text("", 5) == []
    assert wrap_text("   \t\n ", 5) == []


def test_single_word_fits():
    assert wrap_text("hello", 5) == ["hello"]


# ---------- wrap_text: hard split ----------

def test_long_word_hard_split():
    assert wrap_text("abcdefghij", 4) == ["abcd", "efgh", "ij"]


def test_final_piece_can_be_joined_by_following_words():
    assert wrap_text("abcdefghi j", 4) == ["abcd", "efgh", "i j"]


def test_final_piece_does_not_join_when_too_wide():
    assert wrap_text("abcdefghij kl", 4) == ["abcd", "efgh", "ij", "kl"]


def test_long_word_after_text_starts_on_new_line():
    assert wrap_text("hi abcdefg", 4) == ["hi", "abcd", "efg"]


def test_width_one_splits_every_char():
    assert wrap_text("ab c", 1) == ["a", "b", "c"]


def test_zero_width_char_stays_with_preceding_char():
    # "ab" fills width 2; the combining mark must stay with "b", not start a piece.
    assert wrap_text("ab́cd", 2) == ["ab́", "cd"]


def test_zero_width_char_in_middle_of_piece():
    assert wrap_text("ábcd", 2) == ["áb", "cd"]


# ---------- wrap_text: wide characters ----------

def test_wide_chars_split_by_columns():
    assert wrap_text("中文 a", 2) == ["中", "文", "a"]


def test_single_wide_char_wider_than_width_not_dropped():
    assert wrap_text("中", 1) == ["中"]


def test_wide_word_fits_exactly():
    assert wrap_text("中文", 4) == ["中文"]


# ---------- wrap_text: invalid input ----------

@pytest.mark.parametrize("bad", [0, -1, 2.5, "3", None])
def test_invalid_width_raises(bad):
    with pytest.raises(ValueError):
        wrap_text("x", bad)


# ---------- wrap_text: invariant ----------

def test_no_line_exceeds_width_and_no_word_lost():
    text = "lorem ipsum dolor sit amet consectetur adipiscing elit " * 3
    text += "supercalifragilisticexpialidocious"
    for width in range(1, 12):
        lines = wrap_text(text, width)
        assert all(display_width(line) <= width for line in lines)
        assert "".join(lines) == "".join(text.split())
