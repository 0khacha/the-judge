"""SimpleCache -- see SPEC.md."""

import time
from typing import Any, Optional


class SimpleCache:
    """A key-value cache whose entries expire after ``ttl_seconds``."""

    def __init__(self, ttl_seconds: float = 60):
        self.ttl = ttl_seconds
        self._entries: dict[str, tuple[Any, float]] = {}

    def set(self, key: str, value: Any) -> None:
        self._entries[key] = (value, time.time())

    def get(self, key: str) -> Optional[Any]:
        if key not in self._entries:
            return None
        value, stored_at = self._entries[key]
        if time.time() - stored_at > self.ttl:  # R4: still valid at exactly ttl
            del self._entries[key]
            return None
        return value

    def clear(self) -> None:
        self._entries.clear()

    def size(self) -> int:
        return len(self._entries)
