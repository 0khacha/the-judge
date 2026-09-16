from impl import run_query
def test_visible():
    assert run_query('select') == []
