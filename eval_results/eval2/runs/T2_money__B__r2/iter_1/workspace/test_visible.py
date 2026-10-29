from money import to_cents, allocate

def test_to_cents():
    assert to_cents("12.34") == 1234
    assert to_cents("5") == 500
    assert to_cents("-0.5") == -50

def test_allocate():
    assert allocate(100, [1, 1, 2]) == [25, 25, 50]
    assert allocate(10, [1, 1]) == [5, 5]
