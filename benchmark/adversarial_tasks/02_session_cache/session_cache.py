from typing import Any, Dict, Optional

class SessionStore:
    """Session store with configurable expiration."""

    def __init__(self, window_seconds: float = 10.0):
        self.window_seconds = window_seconds
        self.store: Dict[str, Dict[str, Any]] = {}

    def store_session(self, token: str, payload: Any, current_time: float = 0.0) -> None:
        self.store[token] = {
            "payload": payload,
            "created_at": current_time,
        }

    def fetch_session(self, token: str, current_time: float = 0.0) -> Optional[Any]:
        if token not in self.store:
            return None
        
        entry = self.store[token]
        # FLAW: Ignores window_seconds expiration check!
        return entry["payload"]
