from luhn import validate_luhn


def test_luhn_doubled_five_reduction() -> None:
    # Card number containing digit 5 at odd position (doubled=10 -> 10-9=1)
    # 49927398716 -> valid Luhn with 5 doubled
    assert validate_luhn("49927398716") is True
