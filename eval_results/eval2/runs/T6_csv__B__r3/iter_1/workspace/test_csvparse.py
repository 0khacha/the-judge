import pytest

from csvparse import parse_csv


def test_empty_text_gives_no_records():
    assert parse_csv("") == []


def test_simple_lf_and_crlf():
    assert parse_csv("a,b,c\n1,2,3") == [["a", "b", "c"], ["1", "2", "3"]]
    assert parse_csv("a,b\r\nc,d") == [["a", "b"], ["c", "d"]]


def test_final_terminator_does_not_add_record():
    assert parse_csv("a,b\n") == [["a", "b"]]
    assert parse_csv("a,b\r\n") == [["a", "b"]]


def test_blank_line_is_record_with_single_empty_field():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]


def test_trailing_comma_gives_trailing_empty_field():
    assert parse_csv("a,\n") == [["a", ""]]
    assert parse_csv(",") == [["", ""]]


def test_quoted_comma_and_escaped_quote():
    assert parse_csv('x,"hello, world","say ""hi"" "') == [["x", "hello, world", 'say "hi" ']]


def test_quoted_field_keeps_newlines_verbatim():
    assert parse_csv('"a\nb",c') == [["a\nb", "c"]]
    assert parse_csv('"a\r\nb",c') == [["a\r\nb", "c"]]


def test_quoted_empty_field():
    assert parse_csv('"",x') == [["", "x"]]


def test_quote_in_middle_of_unquoted_field_is_literal():
    assert parse_csv('ab"cd,e') == [['ab"cd', "e"]]


def test_whitespace_preserved():
    assert parse_csv(" a , b \n") == [[" a ", " b "]]


def test_quoted_field_followed_by_terminator_or_comma_ok():
    assert parse_csv('"a"\n"b"') == [["a"], ["b"]]
    assert parse_csv('"a","b"') == [["a", "b"]]


def test_quoted_field_followed_by_junk_raises():
    with pytest.raises(ValueError):
        parse_csv('"a"b,c')


def test_quoted_field_followed_by_space_raises():
    with pytest.raises(ValueError):
        parse_csv('"a" ,c')


def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"abc')
    with pytest.raises(ValueError):
        parse_csv('a,"b""')
