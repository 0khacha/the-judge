import time
import pytest
from jwt_auth import encode_token, decode_token, TokenExpiredError


def test_expired_token_rejection() -> None:
    secret = "secret123"
    payload = {"user_id": 42}
    # Token expires in 1 second
    token = encode_token(payload, secret, expires_in=1)
    time.sleep(1.1)
    with pytest.raises(TokenExpiredError):
        decode_token(token, secret)
