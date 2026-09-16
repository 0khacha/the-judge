from discount import calculate_final_price


def test_exact_threshold_boundary_discount() -> None:
    # Exact $100.00 threshold must receive 10% discount -> $90.00
    assert calculate_final_price(100.0) == 90.0
