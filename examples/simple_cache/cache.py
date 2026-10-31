"""SimpleCache -- see SPEC.md. Not implemented yet: that is step 3 of the walk-through."""

from typing import Any, Optional


class SimpleCache:
    """A key-value cache whose entries expire after ``ttl_seconds``."""

    def __init__(self, ttl_seconds: float = 60):
        self.ttl = ttl_seconds

    def set(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def size(self) -> int:
        raise NotImplementedError
