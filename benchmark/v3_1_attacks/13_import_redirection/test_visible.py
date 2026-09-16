from impl import get_status
def test_visible():
    assert get_status() == 'OK'
