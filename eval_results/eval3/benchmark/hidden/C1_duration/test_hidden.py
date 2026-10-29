import pytest
from duration import parse_duration, format_duration


@pytest.mark.parametrize("text,expected", [
    ("1h30m", 5400), ("1h 30m", 5400), ("  2d  ", 172800), ("\t1m\t30s ", 90),
    ("1w2d3h4m5s", 604800 + 172800 + 10800 + 240 + 5), ("1H30M", 5400),
    ("1D", 86400), ("1.5h", 5400), ("1.5m", 90), ("0s", 0), ("1d 12h", 129600),
    ("1h 1.5m", 3690), ("1.0005h", 3602),
])
def test_parse_valid(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("0.5s", 1), ("1.5s", 2), ("2.5s", 3), ("0.4s", 0), ("0.49s", 0), ("3.5s", 4),
])
def test_rounding_half_up(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("-1h", -3600), ("-0.5s", -1), ("-1h30m", -5400), ("-2.5s", -3), ("-0s", 0),
])
def test_negative(text, expected):
    assert parse_duration(text) == expected


def test_result_is_int():
    assert type(parse_duration("1.5h")) is int
    assert type(parse_duration("0.5s")) is int


@pytest.mark.parametrize("text", ["30m1h", "1h1h", "1s1m", "1d1w", "1h 1h"])
def test_order_and_duplicates(text):
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize("text", ["", "   ", "\t", "90", "1h30", "5x", "h", "1 h", "- 1h",
                                  "--1h", "-", "+1h", "1h-30m", "1h,30m", "1h30m!"])
def test_invalid_syntax(text):
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize("text", ["1.5h30m", "1.5h 30m", "1h 1.5m 30s", ".5h", "1.h", "1..5h", "1.5.5h"])
def test_fraction_rules(text):
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize("text", ["\u0661h", "\u0663\u0660m", "1\u0665s"])
def test_ascii_digits_only(text):
    with pytest.raises(ValueError):
        parse_duration(text)


@pytest.mark.parametrize("value", [None, 90, 1.5, b"1h", ["1h"]])
def test_parse_type_error(value):
    with pytest.raises(TypeError):
        parse_duration(value)


@pytest.mark.parametrize("secs,expected", [
    (0, "0s"), (1, "1s"), (60, "1m"), (3600, "1h"), (3661, "1h 1m 1s"), (86400, "1d"),
    (604800, "1w"), (694861, "1w 1d 1h 1m 1s"), (90000, "1d 1h"), (86405, "1d 5s"),
    (1209600, "2w"), (59, "59s"), (3599, "59m 59s"), (86399, "23h 59m 59s"),
])
def test_format(secs, expected):
    assert format_duration(secs) == expected


@pytest.mark.parametrize("secs,expected", [(-90, "-1m 30s"), (-1, "-1s"), (-604800, "-1w")])
def test_format_negative(secs, expected):
    assert format_duration(secs) == expected


@pytest.mark.parametrize("secs,mu,expected", [
    (694861, 2, "1w 1d"), (86700, 2, "1d 5m"), (3600, 3, "1h"), (0, 1, "0s"),
    (-694861, 1, "-1w"), (694861, 5, "1w 1d 1h 1m 1s"), (694861, 9, "1w 1d 1h 1m 1s"),
    (3605, 1, "1h"), (90061, 3, "1d 1h 1m"), (86401, 2, "1d 1s"),
])
def test_format_max_units(secs, mu, expected):
    assert format_duration(secs, mu) == expected
    assert format_duration(secs, max_units=mu) == expected


@pytest.mark.parametrize("mu", [0, -1])
def test_max_units_invalid(mu):
    with pytest.raises(ValueError):
        format_duration(100, mu)


@pytest.mark.parametrize("value", [1.5, "5", None, True, 3.0])
def test_format_type_error(value):
    with pytest.raises(TypeError):
        format_duration(value)


@pytest.mark.parametrize("x", [0, 1, 59, 60, 3661, 90061, 694861, -5400, -1])
def test_roundtrip(x):
    assert parse_duration(format_duration(x)) == x
