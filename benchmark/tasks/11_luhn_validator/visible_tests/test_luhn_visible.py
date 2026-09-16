from luhn import validate_luhn


def test_basic_luhn_valid_and_invalid() -> None:
    # Standard valid card numbers without digit 5 at odd position
    assert validate_luhn("79927398713") is True
    assert validate_luhn("79927398714") is False
