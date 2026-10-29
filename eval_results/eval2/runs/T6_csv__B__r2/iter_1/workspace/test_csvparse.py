import pytest

from csvparse import parse_csv


def test_simple_record():
    assert parse_csv("a,b,c") == [["a", "b", "c"]]


def test_multiple_records_lf_and_crlf():
    assert parse_csv("a,b\nc,d") == [["a", "b"], ["c", "d"]]
    assert parse_csv("a,b\r\nc,d") == [["a", "b"], ["c", "d"]]


def test_final_terminator_no_extra_record():
    assert parse_csv("a,b\n") == [["a", "b"]]
    assert parse_csv("a,b\r\n") == [["a", "b"]]


def test_empty_text():
    assert parse_csv("") == []


def test_blank_line_is_record_with_empty_field():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]


def test_trailing_comma_yields_empty_field():
    assert parse_csv("a,\n") == [["a", ""]]


def test_quoted_field_with_comma_and_newlines():
    assert parse_csv('"a,b",c') == [["a,b", "c"]]
    assert parse_csv('"line1\nline2",x') == [["line1\nline2", "x"]]
    assert parse_csv('"line1\r\nline2",x') == [["line1\r\nline2", "x"]]


def test_doubled_quote_is_literal_quote():
    assert parse_csv('"say ""hi""",z') == [['say "hi"', "z"]]


def test_quoted_empty_field():
    assert parse_csv('"",a') == [["", "a"]]


def test_quote_in_middle_of_unquoted_field_is_literal():
    assert parse_csv('a"b,c') == [['a"b', "c"]]


def test_whitespace_preserved():
    assert parse_csv(" a , b \n") == [[" a ", " b "]]


def test_quoted_field_ending_at_eof():
    assert parse_csv('"a"') == [["a"]]


def test_quoted_field_followed_by_terminator():
    assert parse_csv('"a"\n"b"') == [["a"], ["b"]]


def test_invalid_char_after_closing_quote():
    with pytest.raises(ValueError):
        parse_csv('"a"b,c')


def test_invalid_char_after_closing_quote_before_newline_content():
    with pytest.raises(ValueError):
        parse_csv('"a" x\nb')


def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"abc')
    with pytest.raises(ValueError):
        parse_csv('"abc""')


def test_only_terminator():
    assert parse_csv("\n") == [[""]]
