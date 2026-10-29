from duration import parse_duration, format_duration


def test_parse_basic():
    assert parse_duration("1h30m") == 5400
    assert parse_duration("90s") == 90


def test_format_basic():
    assert format_duration(3661) == "1h 1m 1s"


def test_zero():
    assert format_duration(0) == "0s"
