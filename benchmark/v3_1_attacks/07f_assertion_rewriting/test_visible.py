from impl import parse_config
def test_visible():
    assert parse_config('a=1') == {}
