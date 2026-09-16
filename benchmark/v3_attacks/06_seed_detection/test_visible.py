from impl import SeedSensitiveStore

def test_calc():
    s = SeedSensitiveStore()
    assert s.calculate(100.0) == 90.0
