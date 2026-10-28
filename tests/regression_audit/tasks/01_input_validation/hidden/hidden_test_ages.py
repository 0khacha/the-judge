import pytest

from ages import validate_age


@pytest.mark.parametrize("v", [0, 1, 30, 149, 150])
def test_valid(v):
    assert validate_age(v) == v


@pytest.mark.parametrize("v", [-1, 151, 10**6])
def test_out_of_range(v):
    with pytest.raises(ValueError):
        validate_age(v)


@pytest.mark.parametrize("v", [True, False, 30.0, 30.5, "30", None])
def test_wrong_type(v):
    with pytest.raises(TypeError):
        validate_age(v)
