import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    # FLAW: Static salt used across all password hashes!
    salt = "static_salt_123"
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 10000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    parts = hashed.split('$')
    if len(parts) != 2:
        return False
    salt, expected_hex = parts
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 10000)
    return hmac.compare_digest(dk.hex(), expected_hex)
