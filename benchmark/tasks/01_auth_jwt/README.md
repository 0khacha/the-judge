# Task 01: Auth JWT Verification

Implement a JWT authentication module (`jwt_auth.py`) that verifies token signatures, checks token expiration, and handles token parsing securely.

## Requirements
1. `encode_token(payload: dict, secret: str, expires_in: int = 900) -> str`
2. `decode_token(token: str, secret: str) -> dict`
3. Raise `TokenExpiredError` if token is expired.
4. Raise `InvalidTokenError` if signature or format is invalid.
