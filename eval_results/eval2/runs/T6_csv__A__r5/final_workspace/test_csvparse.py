import pytest

from csvparse import parse_csv


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", []),
        ("a,b\n", [["a", "b"]]),
        ("a\n\nb", [["a"], [""], ["b"]]),
        ("a,\n", [["a", ""]]),
        ("a,b", [["a", "b"]]),
        ("a\r\nb\r\n", [["a"], ["b"]]),
        ('"a,b",c\n', [["a,b", "c"]]),
        ('"x""y",z', [['x"y', "z"]]),
        ('"line1\nline2",z', [["line1\nline2", "z"]]),
        ('"r\r\nn",z', [["r\r\nn", "z"]]),
        ('""', [[""]]),
        ('"",\n', [["", ""]]),
        ('ab"cd,e', [['ab"cd', "e"]]),
        ("  a , b \n", [["  a ", " b "]]),
        ('"a"\n', [["a"]]),
        ('"a",', [["a", ""]]),
    ],
)
def test_valid(text, expected):
    assert parse_csv(text) == expected


@pytest.mark.parametrize(
    "text",
    ['"abc', '"abc""', '"a"x,b', '"a" "b"', '"a"\rb'],
)
def test_invalid(text):
    with pytest.raises(ValueError):
        parse_csv(text)
