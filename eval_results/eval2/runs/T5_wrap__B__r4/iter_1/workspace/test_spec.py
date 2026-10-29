import pytest
from wrap import wrap_text, display_width


# display_width

def test_width_plain_ascii():
    assert display_width("") == 0
    assert display_width("hello") == 5


def test_width_combining_is_zero():
    assert display_width("é") == 1


def test_width_format_char_is_zero():
    assert display_width("a​b") == 2


def test_width_wide_east_asian():
    assert display_width("中") == 2
    assert display_width("中文") == 4


def test_width_fullwidth_latin():
    assert display_width("Ａ") == 2


def test_width_mixed():
    assert display_width("a中é") == 4


# wrap_text: basics and normalisation

def test_empty_and_blank_return_empty_list():
    assert wrap_text("", 5) == []
    assert wrap_text(" \t\n ", 5) == []


def test_whitespace_runs_collapse_including_tabs_and_newlines():
    assert wrap_text("a\tb\nc", 10) == ["a b c"]


def test_exact_fit_on_one_line():
    assert wrap_text("ab cd", 5) == ["ab cd"]


def test_word_exactly_width_not_split():
    assert wrap_text("abcd", 4) == ["abcd"]


def test_greedy_fill():
    assert wrap_text("aaa bbb ccc ddd", 7) == ["aaa bbb", "ccc ddd"]


# wrap_text: hard splitting

def test_long_word_hard_split_final_piece_starts_line():
    assert wrap_text("abcdefghij", 4) == ["abcd", "efgh", "ij"]


def test_long_word_exact_multiple():
    assert wrap_text("abcdefgh", 4) == ["abcd", "efgh"]


def test_long_word_flushes_previous_line_first():
    assert wrap_text("ab cdefghij k", 4) == ["ab", "cdef", "ghij", "k"]


def test_following_word_joins_final_piece():
    # final piece "ef" starts the current line; "h" joins it because "ef h" fits
    assert wrap_text("abcdef h", 4) == ["abcd", "ef h"]


def test_following_word_does_not_join_full_final_piece():
    assert wrap_text("abcdefgh ij", 4) == ["abcd", "efgh", "ij"]


def test_following_word_too_wide_for_final_piece():
    assert wrap_text("abcdefg h", 4) == ["abcd", "efg", "h"]


def test_zero_width_never_starts_new_piece():
    assert wrap_text("éabc", 2) == ["éa", "bc"]


def test_zero_width_stays_with_preceding_char_at_boundary():
    # 'a' + combining mark fills width 1; combining mark must not be separated
    assert wrap_text("áb", 1) == ["á", "b"]


# wrap_text: wide characters

def test_wide_chars_greedy():
    assert wrap_text("中文 字", 4) == ["中文", "字"]


def test_wide_chars_hard_split():
    assert wrap_text("中文字", 4) == ["中文", "字"]


def test_single_wide_char_wider_than_width_kept():
    assert wrap_text("中", 1) == ["中"]


def test_wide_char_alone_when_wider_than_width():
    assert wrap_text("a中b", 1) == ["a", "中", "b"]


# wrap_text: errors

@pytest.mark.parametrize("bad", [0, -1, 2.5, "3", None])
def test_invalid_width_raises(bad):
    with pytest.raises(ValueError):
        wrap_text("x", bad)


# property-style: no line exceeds width unless it is a single wide char

def test_lines_respect_width_property():
    text = "The quick brown fox jumps over the lazy dog, supercalifragilistic style 中文字 done"
    for width in range(2, 12):
        lines = wrap_text(text, width)
        assert "".join(lines).replace(" ", "") == "".join(text.split())
        for line in lines:
            assert display_width(line) <= width or len(line) == 1
