import pytest
from csvparse import parse_csv, parse_csv_dicts, CsvError


@pytest.mark.parametrize("text,expected", [
    ("a,b,c", [["a", "b", "c"]]),
    ("a,b\n1,2", [["a", "b"], ["1", "2"]]),
    ("a,b\r\n1,2\r\n", [["a", "b"], ["1", "2"]]),
    ("a\rb\rc", [["a"], ["b"], ["c"]]),
    ("a\nb\r\nc\rd", [["a"], ["b"], ["c"], ["d"]]),
    ("a,b\n", [["a", "b"]]),
    ("a,b\r", [["a", "b"]]),
    ("", []),
    ("\n", []),
    ("\r\n\r\n", []),
])
def test_separators(text, expected):
    assert parse_csv(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("a\n\nb", [["a"], ["b"]]),
    ("a\r\n\r\nb", [["a"], ["b"]]),
    ("\n\na\n\n", [["a"]]),
    ("a\r\rb", [["a"], ["b"]]),
])
def test_empty_lines_skipped(text, expected):
    assert parse_csv(text) == expected


def test_space_only_line_is_a_record():
    assert parse_csv("a\n  \nb") == [["a"], ["  "], ["b"]]


def test_empty_quoted_line_is_a_record():
    assert parse_csv('a\n""\nb') == [["a"], [""], ["b"]]
    assert parse_csv('""') == [[""]]


@pytest.mark.parametrize("text,expected", [
    ("a,b,", [["a", "b", ""]]),
    (",", [["", ""]]),
    (",a", [["", "a"]]),
    ("a,,b", [["a", "", "b"]]),
    ("a,\nb,", [["a", ""], ["b", ""]]),
    (",,,", [["", "", "", ""]]),
])
def test_empty_fields(text, expected):
    assert parse_csv(text) == expected


def test_whitespace_preserved():
    assert parse_csv(" a , b ,\tc\t") == [[" a ", " b ", "\tc\t"]]
    assert parse_csv('" a ", b') == [[" a ", " b"]]


@pytest.mark.parametrize("text,expected", [
    ('"a,b",c', [["a,b", "c"]]),
    ('"he said ""hi""",x', [['he said "hi"', "x"]]),
    ('""""', [['"']]),
    ('"a""",b', [['a"', "b"]]),
    ('"a\nb",c', [["a\nb", "c"]]),
    ('"a\r\nb",c', [["a\r\nb", "c"]]),
    ('"a\rb"', [["a\rb"]]),
    ('"x"\n"y"', [["x"], ["y"]]),
    ('"a","b"', [["a", "b"]]),
    ('"a",', [["a", ""]]),
    ('"",""', [["", ""]]),
])
def test_quoted(text, expected):
    assert parse_csv(text) == expected


def test_quote_inside_unquoted_is_literal():
    assert parse_csv('ab"c,d') == [['ab"c', "d"]]
    assert parse_csv('a "b" c') == [['a "b" c']]


def test_bom_removed():
    assert parse_csv("\ufeffa,b") == [["a", "b"]]
    assert parse_csv("\ufeff") == []
    assert parse_csv('\ufeff"a"') == [["a"]]


@pytest.mark.parametrize("delim,text,expected", [
    ("\t", "a\tb\tc", [["a", "b", "c"]]),
    (";", "a;b,c;d", [["a", "b,c", "d"]]),
    (";", '"a;b";c', [["a;b", "c"]]),
    ("|", "a|", [["a", ""]]),
])
def test_custom_delimiter(delim, text, expected):
    assert parse_csv(text, delimiter=delim) == expected
    assert parse_csv(text, delim) == expected


@pytest.mark.parametrize("delim", ['"', "\n", "\r", "", ",,", "ab"])
def test_invalid_delimiter(delim):
    with pytest.raises(ValueError) as ei:
        parse_csv("a,b", delimiter=delim)
    assert not isinstance(ei.value, CsvError)


def test_csverror_is_valueerror():
    assert issubclass(CsvError, ValueError)


@pytest.mark.parametrize("text,line", [
    ('"abc', 1),
    ('a\nb,"x', 2),
    ('a,"x\ny"\nb,"z', 3),
    ('"abc""', 1),
    ('a\r\nb\r\n"c', 3),
    ('a\rb\r"c', 3),
    ('a\n\n\n"c', 4),
    ('"a\r\nb\r\nc', 1),
])
def test_unterminated_reports_start_line(text, line):
    with pytest.raises(CsvError) as ei:
        parse_csv(text)
    assert ei.value.line == line


@pytest.mark.parametrize("text,line", [
    ('"a"x', 1),
    ('"a"\n"b"x', 2),
    ('"a\nb"x', 2),
    ('a\n\n"b" ,c', 3),
    ('"a" b', 1),
    ('x\r\n"a\r\nb\r\nc"d', 4),
])
def test_stray_after_quote(text, line):
    with pytest.raises(CsvError) as ei:
        parse_csv(text)
    assert ei.value.line == line


def test_error_line_with_bom():
    with pytest.raises(CsvError) as ei:
        parse_csv('\ufeffa\n"b"x')
    assert ei.value.line == 2


def test_long_mixed():
    text = 'id,name,note\r\n1,"Smith, J","line1\nline2"\r\n\r\n2,Ann,\r\n'
    assert parse_csv(text) == [["id", "name", "note"], ["1", "Smith, J", "line1\nline2"], ["2", "Ann", ""]]


# ---------------------------------------------------------------- dicts

def test_dicts_basic():
    assert parse_csv_dicts("a,b\n1,2\n3,4") == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]


def test_dicts_key_order():
    rows = parse_csv_dicts("z,a,m\n1,2,3")
    assert list(rows[0]) == ["z", "a", "m"]


def test_dicts_empty_and_header_only():
    assert parse_csv_dicts("") == []
    assert parse_csv_dicts("a,b") == []
    assert parse_csv_dicts("a,b\n\n") == []


def test_dicts_pad_short_rows():
    assert parse_csv_dicts("a,b,c\n1\n1,2") == [{"a": "1", "b": "", "c": ""}, {"a": "1", "b": "2", "c": ""}]


def test_dicts_long_row_error():
    with pytest.raises(CsvError):
        parse_csv_dicts("a,b\n1,2,3")


def test_dicts_duplicate_header():
    with pytest.raises(CsvError):
        parse_csv_dicts("a,b,a\n1,2,3")
    with pytest.raises(CsvError):
        parse_csv_dicts("a, a\n1,2")


def test_dicts_empty_header_name():
    with pytest.raises(CsvError):
        parse_csv_dicts("a,,c\n1,2,3")
    with pytest.raises(CsvError):
        parse_csv_dicts("a, ,c\n1,2,3")


def test_dicts_header_stripped_values_not():
    assert parse_csv_dicts(' a ,"b "\n x , y ') == [{"a": " x ", "b": " y "}]


def test_dicts_bom_and_delimiter():
    assert parse_csv_dicts("\ufeffa;b\n1;2", delimiter=";") == [{"a": "1", "b": "2"}]


def test_dicts_propagates_parse_errors():
    with pytest.raises(CsvError) as ei:
        parse_csv_dicts('a\n"x')
    assert ei.value.line == 2
    with pytest.raises(ValueError):
        parse_csv_dicts("a,b", delimiter='"')
