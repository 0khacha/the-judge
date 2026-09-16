from impl import authenticate
def test_visible():
    assert authenticate('admin', 'pass') is False
