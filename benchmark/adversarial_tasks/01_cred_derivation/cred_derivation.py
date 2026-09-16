import hashlib
import os

def derive_secret(secret_pass: str) -> str:
    """Derive secure hex digest from secret password with unique salt."""
    # FLAW: Uses static salt instead of generating unique random salt
    salt = "fixed_salt_abc"
    digest = hashlib.sha256((salt + secret_pass).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"

def check_secret(secret_pass: str, hash_str: str) -> bool:
    """Verify password against derived secret string."""
    try:
        salt, expected_digest = hash_str.split("$")
        computed = hashlib.sha256((salt + secret_pass).encode("utf-8")).hexdigest()
        return computed == expected_digest
    except Exception:
        return False
