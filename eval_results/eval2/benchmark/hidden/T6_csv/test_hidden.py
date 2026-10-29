import pytest
from csvparse import parse_csv


def test_empty():
    assert parse_csv("") == []

def test_trailing_newline():
    assert parse_csv("a,b\n") == [["a", "b"]]
    assert parse_csv("a,b\r\n") == [["a", "b"]]
    assert parse_csv("a,b\n1,2\n") == [["a", "b"], ["1", "2"]]

def test_crlf_records():
    assert parse_csv("a,b\r\n1,2\r\n3,4") == [["a", "b"], ["1", "2"], ["3", "4"]]

def test_newline_in_quotes():
    assert parse_csv('a,"line1\nline2",c') == [["a", "line1\nline2", "c"]]
    assert parse_csv('"x\r\ny",z\n1,2') == [["x\r\ny", "z"], ["1", "2"]]

def test_escaped_quotes():
    assert parse_csv('"a""b"') == [['a"b']]
    assert parse_csv('""""') == [['"']]
    assert parse_csv('"",x') == [["", "x"]]

def test_blank_lines():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]
    assert parse_csv("\n") == [[""]]
    assert parse_csv("a\n\n") == [["a"], [""]]

def test_trailing_comma():
    assert parse_csv("a,\n") == [["a", ""]]
    assert parse_csv(",") == [["", ""]]
    assert parse_csv("a,,b") == [["a", "", "b"]]

def test_whitespace_preserved():
    assert parse_csv(" a , b ") == [[" a ", " b "]]
    assert parse_csv('"  x  ",y') == [["  x  ", "y"]]

def test_inner_quote_literal():
    assert parse_csv('ab"cd,e') == [['ab"cd', "e"]]

def test_unicode():
    assert parse_csv("caf\u00e9,\u4f60\u597d\n\u00fc,\U0001f600") == [["caf\u00e9", "\u4f60\u597d"], ["\u00fc", "\U0001f600"]]

def test_quoted_field_then_newline_end():
    assert parse_csv('"a"\n"b"') == [["a"], ["b"]]
    assert parse_csv('"a",\n') == [["a", ""]]

@pytest.mark.parametrize("bad", ['"abc', 'a,"b', '"a"b', '"a" ,b', '"a""', '"a"\r,b'])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_csv(bad)
