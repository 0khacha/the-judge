import pytest

from durations import parse_duration


@pytest.mark.parametrize("s,expected", [
    ("90s", 90), ("2m", 120), ("1h", 3600), ("1h30m", 5400), ("1h2m3s", 3723), ("0s", 0),
])
def test_valid(s, expected):
    assert parse_duration(s) == expected


@pytest.mark.parametrize("s", ["", "abc", "1h1h", "10", "10sxyz", "h", "1x", " 1h"])
def test_invalid(s):
    with pytest.raises(ValueError):
        parse_duration(s)
