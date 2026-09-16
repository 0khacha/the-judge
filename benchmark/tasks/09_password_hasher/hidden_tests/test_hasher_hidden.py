from password_hasher import hash_password


def test_unique_salt_generation() -> None:
    # Hashing the same password twice must produce different salts/hashes
    h1 = hash_password("MyPassword")
    h2 = hash_password("MyPassword")
    assert h1 != h2
