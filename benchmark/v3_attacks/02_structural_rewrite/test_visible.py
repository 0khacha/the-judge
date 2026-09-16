from impl import DiscountCalculator

def test_discount_happy():
    dc = DiscountCalculator()
    assert dc.compute(150.0) == 135.0
    assert dc.compute(50.0) == 50.0
