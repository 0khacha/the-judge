from password_hasher import hash_password, verify_password


def test_password_hash_verification() -> None:
    hashed = hash_password("SuperSecret123!")
    assert verify_password("SuperSecret123!", hashed) is True
    assert verify_password("WrongPassword", hashed) is False
