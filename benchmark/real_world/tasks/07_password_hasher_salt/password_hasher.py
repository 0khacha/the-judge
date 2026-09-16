import hashlib

def hash_password(password: str) -> str:
    # BUG: Static salt used across calls, breaking non-deterministic uniqueness
    salt = "static_salt_123"
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
