import pytest
from jwt_auth import encode_token, decode_token, InvalidTokenError


def test_valid_token_encode_decode() -> None:
    secret = "secret123"
    payload = {"user_id": 42, "role": "admin"}
    token = encode_token(payload, secret)
    decoded = decode_token(token, secret)
    assert decoded["user_id"] == 42
    assert decoded["role"] == "admin"


def test_invalid_signature_rejection() -> None:
    token = encode_token({"user_id": 42}, "correct_secret")
    with pytest.raises(InvalidTokenError):
        decode_token(token, "wrong_secret")
