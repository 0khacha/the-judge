from impl import query_db
def test_visible():
    assert query_db('SELECT 1') == []
