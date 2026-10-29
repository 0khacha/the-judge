from wrap import wrap_text, display_width


def test_simple():
    assert wrap_text("the quick brown fox jumps", 10) == "the quick\nbrown fox\njumps"


def test_paragraphs():
    assert wrap_text("aaa\n\n\nbbb", 20) == "aaa\n\nbbb"


def test_width():
    assert display_width("abc") == 3
