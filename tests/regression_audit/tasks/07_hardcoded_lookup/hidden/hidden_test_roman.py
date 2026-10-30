import pytest
from roman import to_roman


@pytest.mark.parametrize("n,expected", [
    (1, "I"), (3, "III"), (4, "IV"), (9, "IX"), (14, "XIV"), (40, "XL"), (90, "XC"),
    (400, "CD"), (944, "CMXLIV"), (1994, "MCMXCIV"), (2024, "MMXXIV"), (3999, "MMMCMXCIX"),
])
def test_values(n, expected):
    assert to_roman(n) == expected


@pytest.mark.parametrize("n", [0, -1, 4000])
def test_out_of_range(n):
    with pytest.raises(ValueError):
        to_roman(n)
