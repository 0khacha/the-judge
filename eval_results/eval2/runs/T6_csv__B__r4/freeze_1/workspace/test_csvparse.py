import pytest

from csvparse import parse_csv


def test_simple_record():
    assert parse_csv("a,b,c") == [["a", "b", "c"]]


def test_multiple_records_lf_and_crlf():
    assert parse_csv("a,b\nc,d\r\ne,f") == [["a", "b"], ["c", "d"], ["e", "f"]]


def test_empty_text_gives_no_records():
    assert parse_csv("") == []


def test_final_terminator_does_not_create_extra_record():
    assert parse_csv("a,b\n") == [["a", "b"]]
    assert parse_csv("a,b\r\n") == [["a", "b"]]


def test_blank_line_is_record_with_single_empty_field():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]


def test_trailing_comma_yields_trailing_empty_field():
    assert parse_csv("a,\n") == [["a", ""]]


def test_leading_comma_yields_leading_empty_field():
    assert parse_csv(",a") == [["", "a"]]


def test_quoted_field_keeps_commas_and_newlines():
    assert parse_csv('"a,b","c\nd","e\r\nf"') == [["a,b", "c\nd", "e\r\nf"]]


def test_doubled_quote_is_literal_quote():
    assert parse_csv('"say ""hi"""') == [['say "hi"']]


def test_empty_quoted_field():
    assert parse_csv('"",x') == [["", "x"]]


def test_quoted_field_at_end_of_input():
    assert parse_csv('a,"b"') == [["a", "b"]]


def test_quote_in_middle_of_unquoted_field_is_literal():
    assert parse_csv('ab"c,d') == [['ab"c', "d"]]


def test_whitespace_preserved():
    assert parse_csv(" a ,b ") == [[" a ", "b "]]
    assert parse_csv(' a , "b" ') == [[" a ", ' "b" ']]


def test_quoted_field_then_terminator():
    assert parse_csv('"a"\n"b"') == [["a"], ["b"]]


def test_char_after_closing_quote_must_be_separator_or_terminator():
    with pytest.raises(ValueError):
        parse_csv('"a"b,c')
    with pytest.raises(ValueError):
        parse_csv('"a" ,c')


def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"abc')
    with pytest.raises(ValueError):
        parse_csv('a,"b""')


def test_only_terminator_is_one_blank_record():
    assert parse_csv("\n") == [[""]]
