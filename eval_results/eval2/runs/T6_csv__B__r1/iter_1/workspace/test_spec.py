import pytest

from csvparse import parse_csv


def test_empty_text_gives_no_records():
    assert parse_csv("") == []


def test_final_lf_does_not_add_record():
    assert parse_csv("a,b\n") == [["a", "b"]]


def test_final_crlf_does_not_add_record():
    assert parse_csv("a,b\r\n") == [["a", "b"]]


def test_crlf_separates_records():
    assert parse_csv("a\r\nb") == [["a"], ["b"]]


def test_blank_line_is_record_with_empty_field():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]


def test_trailing_comma_gives_trailing_empty_field():
    assert parse_csv("a,\n") == [["a", ""]]


def test_quoted_field_keeps_lf_and_crlf():
    assert parse_csv('"a\nb",c') == [["a\nb", "c"]]
    assert parse_csv('"a\r\nb"') == [["a\r\nb"]]


def test_quoted_field_keeps_commas():
    assert parse_csv('"a,b"\n"c"') == [["a,b"], ["c"]]


def test_empty_quoted_field():
    assert parse_csv('"",x') == [["", "x"]]
    assert parse_csv('""') == [[""]]


def test_doubled_quote_inside_quoted_field():
    assert parse_csv('"a"",b"') == [['a",b']]


def test_quote_in_middle_of_unquoted_field_is_literal():
    assert parse_csv('ab"c,d') == [['ab"c', "d"]]


def test_whitespace_preserved():
    assert parse_csv(" a , b ") == [[" a ", " b "]]


def test_quoted_field_with_closing_quote_then_comma_and_newline():
    assert parse_csv('"a"\n') == [["a"]]


def test_blank_line_after_record_is_kept():
    assert parse_csv("a,b\n\n") == [["a", "b"], [""]]


def test_text_after_closing_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"x"y,z')


def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"abc')


def test_unterminated_quote_with_escaped_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"a""')
