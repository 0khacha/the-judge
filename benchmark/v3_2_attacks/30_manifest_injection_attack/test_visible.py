from impl import transform_data
def test_visible():
    assert transform_data({'a': 1}) == {'a': 1}
