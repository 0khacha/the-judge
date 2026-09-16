import pytest
from cred_derivation import derive_secret, check_secret

def test_derive_secret_returns_valid_format() -> None:
    res = derive_secret("MyPassword123")
    assert "$" in res
    assert check_secret("MyPassword123", res) is True
    assert check_secret("WrongPassword", res) is False
