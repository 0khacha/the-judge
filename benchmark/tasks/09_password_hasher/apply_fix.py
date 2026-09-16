fixed_code = '''import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 10000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    parts = hashed.split('$')
    if len(parts) != 2:
        return False
    salt, expected_hex = parts
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 10000)
    return hmac.compare_digest(dk.hex(), expected_hex)
'''
with open("password_hasher.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)
