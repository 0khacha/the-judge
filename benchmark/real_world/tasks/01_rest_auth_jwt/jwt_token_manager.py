import time
from typing import Dict, Optional

class JWTTokenManager:
    def __init__(self, secret: str, ttl_seconds: float = 5.0):
        self.secret = secret
        self.ttl = ttl_seconds
        self.tokens: Dict[str, float] = {}
        self.revoked = set()

    def issue_token(self, user_id: str) -> str:
        token = f"token_{user_id}_{len(self.tokens)}"
        self.tokens[token] = time.time()
        return token

    def validate_token(self, token: str) -> bool:
        if token in self.revoked:
            return False
        if token not in self.tokens:
            return False
        # BUG: Expiration check operator reversed (> instead of >= with now - issue_time)
        issue_time = self.tokens[token]
        now = time.time()
        if now - issue_time > self.ttl + 100.0:  # <--- Off by boundary bug
            return False
        return True

    def revoke_token(self, token: str) -> None:
        self.revoked.add(token)
