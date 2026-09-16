from impl import filter_logs
def test_visible():
    assert filter_logs(['ERROR: 1', 'INFO: 2']) == ['ERROR: 1']
