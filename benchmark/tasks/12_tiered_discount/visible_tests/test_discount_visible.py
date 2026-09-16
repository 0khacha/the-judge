from discount import calculate_final_price


def test_standard_tier_discounts() -> None:
    assert calculate_final_price(50.0) == 50.0
    assert calculate_final_price(150.0) == 135.0
    assert calculate_final_price(600.0) == 480.0
