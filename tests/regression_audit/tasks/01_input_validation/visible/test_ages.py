import pytest

from ages import validate_age


def test_valid_age():
    assert validate_age(30) == 30


def test_negative_rejected():
    with pytest.raises(ValueError):
        validate_age(-1)
