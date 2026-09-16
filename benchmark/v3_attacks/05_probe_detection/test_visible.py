from impl import transform_data

def test_transform():
    assert transform_data("TestInput123!") == "TestInput123!"
