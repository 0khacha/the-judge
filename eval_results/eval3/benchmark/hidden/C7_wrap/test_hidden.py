import pytest
from wrap import wrap_text, display_width

NB = chr(0xA0)
IDSP = chr(0x3000)
ACUTE = chr(0x301)
RI, BEN, GO = chr(0x65E5), chr(0x672C), chr(0x8A9E)
FA, FB, FC = chr(0xFF21), chr(0xFF22), chr(0xFF23)
E = "e" + ACUTE


@pytest.mark.parametrize("s,w", [
    ("", 0), ("abc", 3), (RI + BEN, 4), (E, 1), (FA + FB, 4), ("a" + chr(0x20DD), 1),
    (chr(0xAC00), 2), (chr(0xFF71), 1), ("a" + RI, 3), (E * 3, 3), (IDSP, 2), (NB, 1),
])
def test_display_width(s, w):
    assert display_width(s) == w


@pytest.mark.parametrize("text,width,exp", [
    ("the quick brown fox jumps", 10, "the quick\nbrown fox\njumps"),
    ("the quick", 9, "the quick"),
    ("the quick", 8, "the\nquick"),
    ("a  b\t\tc\nd", 20, "a b c d"),
    ("   hello   world  ", 20, "hello world"),
    ("aaa\nbbb", 20, "aaa bbb"),
])
def test_basic_filling(text, width, exp):
    assert wrap_text(text, width) == exp


@pytest.mark.parametrize("text,exp", [
    ("aaa bbb\n\n\n   \nccc", "aaa bbb\n\nccc"),
    ("\n\nhello\n\n", "hello"),
    ("aaa\n  \t \nbbb", "aaa\n\nbbb"),
    ("aaa\r\n\r\nbbb", "aaa\n\nbbb"),
    ("aaa\r\rbbb", "aaa\n\nbbb"),
    ("aaa\rbbb", "aaa bbb"),
    ("a\n\nb\n\nc", "a\n\nb\n\nc"),
])
def test_paragraphs_and_line_endings(text, exp):
    assert wrap_text(text, 20) == exp


@pytest.mark.parametrize("text", ["", "   \n \t", "\n\n", "\r\n \r\n"])
def test_no_words(text):
    assert wrap_text(text, 20) == ""


def test_nbsp_is_not_whitespace():
    assert wrap_text("aaa" + NB + "bbb ccc", 8) == "aaa" + NB + "bbb\nccc"
    assert wrap_text("aaa\n" + NB + "\nbbb", 20) == "aaa " + NB + " bbb"


def test_ideographic_space_is_not_whitespace():
    assert wrap_text("a" + IDSP + "b c", 20) == "a" + IDSP + "b c"
    assert wrap_text("a" + IDSP + "b", 3) == "a" + IDSP + "\nb"


def test_indent():
    assert wrap_text("aaa bbb ccc", 8, indent="* ", subsequent_indent="  ") == "* aaa\n  bbb\n  ccc"
    assert wrap_text("aaa bbb", 8, indent="* ") == "* aaa\nbbb"
    assert wrap_text("aaa bbb", 20, subsequent_indent="  ") == "aaa bbb"


def test_indent_restarts_each_paragraph():
    assert wrap_text("aaa\n\nbbb", 10, "> ", "  ") == "> aaa\n\n> bbb"
    assert wrap_text("aaa bbb ccc\n\nddd", 8, "> ", "  ") == "> aaa\n  bbb\n  ccc\n\n> ddd"


@pytest.mark.parametrize("width,indent,sub,ok", [
    (3, "  ", "", False), (4, "  ", "", True), (3, "", "  ", False), (4, "", "  ", True),
    (1, "", "", False), (2, "", "", True), (0, "", "", False), (-5, "", "", False),
    (3, RI, "", False), (4, RI, "", True),
])
def test_width_validation(width, indent, sub, ok):
    if ok:
        wrap_text("ab", width, indent, sub)
    else:
        with pytest.raises(ValueError):
            wrap_text("ab", width, indent, sub)


@pytest.mark.parametrize("text,width,exp", [
    ("abcdefghij", 4, "abcd\nefgh\nij"),
    ("ab abcdefghij", 4, "ab\nabcd\nefgh\nij"),
    ("abcdef h", 4, "abcd\nef h"),
    ("abcdefghij kl", 4, "abcd\nefgh\nij\nkl"),
    ("abcd", 4, "abcd"),
])
def test_hard_break(text, width, exp):
    assert wrap_text(text, width) == exp


def test_hard_break_uses_indent_widths():
    assert wrap_text("abcdefghijkl", 6, "", "  ") == "abcdef\n  ghij\n  kl"
    assert wrap_text("abcdefgh", 5, "> ", "") == "> abc\ndefgh"


@pytest.mark.parametrize("text,width,exp", [
    ("well-known fact", 5, "well-\nknown\nfact"),
    ("well-known fact", 10, "well-known\nfact"),
    ("ab-cd", 3, "ab-\ncd"),
    ("1-2", 2, "1-\n2"),
    ("state-of-the-art", 8, "state-\nof-the-\nart"),
    ("a--b", 3, "a--\nb"),
    ("-ab-", 3, "-ab\n-"),
])
def test_hyphen_breaks(text, width, exp):
    assert wrap_text(text, width) == exp


def test_hyphen_no_break_when_it_fits():
    assert wrap_text("well-known", 10) == "well-known"


@pytest.mark.parametrize("text,width,exp", [
    (RI + BEN + GO + RI + BEN + GO, 6, RI + BEN + GO + "\n" + RI + BEN + GO),
    (RI + BEN + GO + RI + BEN + GO, 5, RI + BEN + "\n" + GO + RI + "\n" + BEN + GO),
    ("ab " + RI + BEN, 5, "ab\n" + RI + BEN),
    ("ab " + RI + BEN, 7, "ab " + RI + BEN),
    (FA + FB + FC, 4, FA + FB + "\n" + FC),
    ("a" + RI + BEN, 3, "a" + RI + "\n" + BEN),
])
def test_wide_characters(text, width, exp):
    assert wrap_text(text, width) == exp


@pytest.mark.parametrize("text,width,exp", [
    (E * 3, 3, E * 3),
    (E * 3, 2, E * 2 + "\n" + E),
    ("abc" + ACUTE, 3, "abc" + ACUTE),
    ("ab" + ACUTE + "cd", 3, "ab" + ACUTE + "c\nd"),
    ("abc" + ACUTE + "d", 3, "abc" + ACUTE + "\nd"),
    ("a " + E + E, 3, "a\n" + E + E),
])
def test_combining_marks(text, width, exp):
    assert wrap_text(text, width) == exp


def test_lines_fit_and_have_no_trailing_space():
    text = ("The quick brown fox, which is well-known for jumping over lazy dogs, "
            "met an extraordinarily-long-hyphenated-word and a " + RI + BEN + GO + RI * 5 + " friend.\n\n"
            "Second paragraph with   spaces\tand supercalifragilisticexpialidocious words.")
    for width in (7, 10, 17, 40):
        out = wrap_text(text, width, "- ", "  ")
        for line in out.split("\n"):
            assert display_width(line) <= width
            assert line == line.rstrip(" ")


def test_no_text_lost():
    text = "alpha beta-gamma delta epsilon " + RI + BEN + " zeta"
    out = wrap_text(text, 9)
    assert "".join(out.split()) == "".join(text.split())
