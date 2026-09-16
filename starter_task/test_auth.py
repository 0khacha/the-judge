import time
import pytest
from auth import (
    PasswordResetService,
    TokenExpiredError,
    InvalidTokenError,
)


def test_request_reset_valid_email() -> None:
    service = PasswordResetService()
    token = service.request_reset("user@example.com")
    assert isinstance(token, str)
    assert len(token) >= 32


def test_verify_token_single_use() -> None:
    service = PasswordResetService()
    token = service.request_reset("user@example.com")
    
    # First verification succeeds
    email = service.verify_reset_token(token)
    assert email == "user@example.com"

    # Second verification fails (replay prevention)
    with pytest.raises(InvalidTokenError):
        service.verify_reset_token(token)


def test_token_expiry() -> None:
    """E1: Token must expire after 15 minutes (900 seconds)."""
    service = PasswordResetService(token_expiry_seconds=900)
    token = service.request_reset("user@example.com")

    start_time = time.time()
    future_time = start_time + 901  # Exceeded 15 minutes

    with pytest.raises(TokenExpiredError):
        service.verify_reset_token(token, current_time=future_time)


def test_invalid_token() -> None:
    service = PasswordResetService()
    with pytest.raises(InvalidTokenError):
        service.verify_reset_token("nonexistent_token_123")


def test_security_token_format() -> None:
    service = PasswordResetService()
    token = service.request_reset("user@example.com")
    assert not token.startswith("mock_")
    assert len(token) > 20
