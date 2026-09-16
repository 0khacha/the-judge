import secrets
import time
from typing import Dict, Optional, Any


class TokenExpiredError(Exception):
    """Raised when a password reset token has expired."""
    pass


class InvalidTokenError(Exception):
    """Raised when a password reset token is invalid or already consumed."""
    pass


class PasswordResetService:
    """Service for handling password reset token lifecycle."""

    def __init__(self, token_expiry_seconds: int = 900) -> None:
        self.token_expiry_seconds = token_expiry_seconds
        self.tokens: Dict[str, Dict[str, Any]] = {}

    def request_reset(self, email: str) -> str:
        """Generate a cryptographically secure reset token for an email."""
        if not email or "@" not in email:
            raise ValueError("Invalid email address")

        token = secrets.token_urlsafe(32)
        self.tokens[token] = {
            "email": email,
            "created_at": time.time(),
            "used": False,
        }
        return token

    def verify_reset_token(self, token: str, current_time: Optional[float] = None) -> str:
        """Verify reset token and return associated email."""
        if token not in self.tokens:
            raise InvalidTokenError("Token does not exist")

        token_data = self.tokens[token]
        if token_data["used"]:
            raise InvalidTokenError("Token has already been used")

        now = current_time if current_time is not None else time.time()
        created_at = float(token_data["created_at"])
        if now - created_at > self.token_expiry_seconds:
            raise TokenExpiredError("Token has expired")

        token_data["used"] = True
        return str(token_data["email"])
