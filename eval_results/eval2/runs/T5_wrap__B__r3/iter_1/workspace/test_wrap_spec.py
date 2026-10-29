import pytest
from wrap import wrap_text, display_width


# ---- display_width -------------------------------------------------------

def test_display_width_ascii():
    assert display_width("") == 0
    assert display_width("hello") == 5


def test_display_width_wide_chars():
    assert display_width("中") == 2
    assert display_width("中文") == 4
    assert display_width("Ａ") == 2  # fullwidth latin, east_asian_width "F"


def test_display_width_combining_and_format_chars_are_zero():
    assert display_width("e\u0301") == 1  # e + combining acute
    assert display_width("\u0301") == 0  # lone combining mark (Mn)
    assert display_width("a\u200bb") == 2  # zero width space (Cf)
    assert display_width("a\u200db") == 2  # zero width joiner (Cf)


def test_display_width_mixed():
    assert display_width("a中e\u0301") == 4


# ---- wrap_text: normal cases --------------------------------------------

def test_empty_and_blank_return_empty_list():
    assert wrap_text("", 10) == []
    assert wrap_text("  \t\n ", 10) == []


def test_whitespace_collapsed_and_greedy_fill():
    assert wrap_text("a   b\tc\n d", 10) == ["a b c d"]
    assert wrap_text("aa bb cc", 5) == ["aa bb", "cc"]


def test_exact_fit_stays_on_one_line():
    assert wrap_text("aa bb", 5) == ["aa bb"]


def test_word_exactly_width_not_split():
    assert wrap_text("abcde", 5) == ["abcde"]
    assert wrap_text("ab cdefg", 5) == ["ab", "cdefg"]


def test_wrapping_at_word_boundaries_no_split():
    assert wrap_text("the quick brown fox", 10) == ["the quick", "brown fox"]


# ---- wrap_text: hard split of long words ---------------------------------

def test_long_word_hard_split_into_pieces():
    assert wrap_text("abcdefghi", 3) == ["abc", "def", "ghi"]


def test_final_piece_is_current_line_and_words_may_join():
    assert wrap_text("abcdefgh ij", 6) == ["abcdef", "gh ij"]


def test_final_piece_does_not_join_when_too_wide():
    assert wrap_text("abcdefgh ij", 5) == ["abcde", "fgh", "ij"]


def test_long_word_after_text_starts_on_new_line():
    assert wrap_text("ab abcdefgh", 5) == ["ab", "abcde", "fgh"]


# ---- wrap_text: wide and zero-width characters ---------------------------

def test_wide_chars_count_two_columns():
    assert wrap_text("中文字", 5) == ["中文", "字"]
    assert wrap_text("中 ab", 3) == ["中", "ab"]


def test_single_char_wider_than_width_placed_alone_not_dropped():
    assert wrap_text("中a", 1) == ["中", "a"]


def test_zero_width_char_attaches_to_preceding_char():
    # "abe" + combining acute fills width 3; combining mark must not start a piece
    assert wrap_text("abe\u0301cd", 3) == ["abe\u0301", "cd"]


def test_zero_width_char_does_not_add_columns():
    assert wrap_text("e\u0301e\u0301", 2) == ["e\u0301e\u0301"]


# ---- wrap_text: invalid input --------------------------------------------

@pytest.mark.parametrize("bad", [0, -1, 2.5, "3", None])
def test_invalid_width_raises_value_error(bad):
    with pytest.raises(ValueError):
        wrap_text("hello", bad)


def test_width_one_is_valid():
    assert wrap_text("ab cd", 1) == ["a", "b", "c", "d"]
