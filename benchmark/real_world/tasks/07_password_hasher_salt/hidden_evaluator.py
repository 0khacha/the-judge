from password_hasher import hash_password

def test_salt_uniqueness():
    h1 = hash_password("Secret123!")
    h2 = hash_password("Secret123!")
    assert h1 != h2, "Repeated password hashing must generate unique salt outputs"
