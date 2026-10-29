import pytest
from wrap import wrap_text, display_width


# display_width: normal, combining, zero-width (Cf), wide (W/F) cases

def test_width_empty():
    assert display_width("") == 0


def test_width_plain_ascii():
    assert display_width("hello world") == 11


def test_width_precomposed_latin_is_one():
    assert display_width("é") == 1


def test_width_combining_sequence():
    # 'e' + combining acute accent: the accent (Mn) adds no columns
    assert display_width("é") == 1


def test_width_lone_combining_mark_is_zero():
    assert display_width("́") == 0


def test_width_variation_selector_is_zero():
    assert display_width("️") == 0


def test_width_zero_width_space_is_zero():
    # U+200B is category Cf
    assert display_width("​") == 0


def test_width_zero_width_joiner_is_zero():
    # U+200D is category Cf
    assert display_width("a‍b") == 2


def test_width_cjk_wide_chars_are_two():
    assert display_width("中") == 2
    assert display_width("中文") == 4


def test_width_mixed_wide_and_narrow():
    assert display_width("a中 b") == 5


# wrap_text: basic greedy fill

def test_wrap_empty_and_blank_returns_empty_list():
    assert wrap_text("", 5) == []
    assert wrap_text("\n\t  ", 5) == []


def test_wrap_collapses_whitespace_runs():
    assert wrap_text("a\n\nb\tc", 10) == ["a b c"]


def test_wrap_greedy_fill_line_breaks():
    assert wrap_text("a b c", 3) == ["a b", "c"]


def test_wrap_exact_fit_single_line():
    assert wrap_text("abc", 3) == ["abc"]


def test_wrap_word_equal_to_width_gets_own_line():
    assert wrap_text("ab cd", 2) == ["ab", "cd"]


def test_wrap_width_one_each_word_own_line():
    assert wrap_text("a b", 1) == ["a", "b"]


def test_wrap_word_with_wide_char_joins_when_it_fits():
    # "中文" is 4 columns, exactly the width; "ab" cannot join
    assert wrap_text("中文 ab", 4) == ["中文", "ab"]


# wrap_text: hard split of over-wide words

def test_hard_split_long_word():
    assert wrap_text("abcdefg", 3) == ["abc", "def", "g"]


def test_hard_split_final_piece_can_take_following_word():
    assert wrap_text("abcdefg h", 3) == ["abc", "def", "g h"]


def test_hard_split_flushes_current_line_before_long_word():
    assert wrap_text("hi abcdef", 3) == ["hi", "abc", "def"]


def test_hard_split_final_piece_does_not_join_when_too_wide():
    assert wrap_text("abcdefg hi", 3) == ["abc", "def", "g", "hi"]


# wrap_text: zero-width characters never start a new piece

def test_zero_width_mark_stays_with_preceding_char():
    # pieces: "áb" (2 cols), then "c"
    assert wrap_text("ábc", 2) == ["áb", "c"]


def test_zero_width_mark_at_piece_boundary_attaches_to_previous():
    assert wrap_text("ab́c", 2) == ["ab́", "c"]


# wrap_text: wide characters

def test_single_wide_char_wider_than_width_placed_alone():
    assert wrap_text("中文", 1) == ["中", "文"]


def test_wide_char_among_narrow_chars_width_one():
    assert wrap_text("a中b", 1) == ["a", "中", "b"]


# wrap_text: invalid width

@pytest.mark.parametrize("bad", [0, -1, 2.0, "3", None])
def test_invalid_width_raises_value_error(bad):
    with pytest.raises(ValueError):
        wrap_text("x", bad)


# wrap_text: invariant on normal inputs

def test_lines_respect_width_on_ordinary_text():
    text = "the quick brown fox jumps over the lazy dog again and again"
    for width in range(5, 20):
        lines = wrap_text(text, width)
        assert " ".join(lines).split() == text.split()
        for line in lines:
            assert display_width(line) <= width
