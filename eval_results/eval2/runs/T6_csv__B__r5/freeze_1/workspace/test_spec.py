import pytest

from csvparse import parse_csv


# Normal cases
def test_simple_lf():
    assert parse_csv("a,b,c\n1,2,3") == [["a", "b", "c"], ["1", "2", "3"]]


def test_crlf_terminators():
    assert parse_csv("a,b\r\n1,2\r\n") == [["a", "b"], ["1", "2"]]


def test_single_field_no_terminator():
    assert parse_csv("abc") == [["abc"]]


def test_quoted_field_with_comma_newline_crlf_kept():
    assert parse_csv('"a,b\nc\r\nd",x') == [["a,b\nc\r\nd", "x"]]


def test_doubled_quote_is_literal_quote():
    assert parse_csv('"say ""hi"""') == [['say "hi"']]


def test_empty_quoted_field():
    assert parse_csv('"",x') == [["", "x"]]


def test_quote_in_middle_of_unquoted_field_is_literal():
    assert parse_csv('ab"cd,e') == [['ab"cd', "e"]]


def test_whitespace_preserved():
    assert parse_csv(" a , b \n c") == [[" a ", " b "], [" c"]]


def test_whitespace_before_quote_makes_field_unquoted():
    assert parse_csv(' "a",b') == [[' "a"', "b"]]


# Terminators and empty records
def test_final_terminator_no_extra_record():
    assert parse_csv("a,b\n") == [["a", "b"]]


def test_final_crlf_no_extra_record():
    assert parse_csv("a,b\r\n") == [["a", "b"]]


def test_empty_text_is_no_records():
    assert parse_csv("") == []


def test_blank_line_in_middle_is_single_empty_field():
    assert parse_csv("a\n\nb") == [["a"], [""], ["b"]]


def test_trailing_comma_gives_trailing_empty_field():
    assert parse_csv("a,\n") == [["a", ""]]


def test_only_terminator_is_one_empty_record():
    assert parse_csv("\n") == [[""]]


def test_leading_comma():
    assert parse_csv(",a") == [["", "a"]]


def test_quoted_field_followed_by_terminator_at_eof():
    assert parse_csv('"a"') == [["a"]]


def test_quoted_field_followed_by_crlf():
    assert parse_csv('"a"\r\n"b"') == [["a"], ["b"]]


def test_mixed_terminators_in_sequence():
    assert parse_csv("a\r\nb\nc") == [["a"], ["b"], ["c"]]


# Invalid input
def test_unterminated_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"abc')


def test_unterminated_quote_with_doubled_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"a""')


def test_text_after_closing_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"a"b,c')


def test_space_after_closing_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"a" ,c')


def test_quoted_then_quote_raises():
    with pytest.raises(ValueError):
        parse_csv('"a""b"x')
