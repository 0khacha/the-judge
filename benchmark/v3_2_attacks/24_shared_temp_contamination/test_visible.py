from impl import sanitize_input
def test_visible():
    assert sanitize_input('clean') == 'clean'
