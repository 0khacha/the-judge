fixed_code = '''import time
from typing import Any, Dict, Optional, Tuple


class LRUCache:
    def __init__(self, capacity: int, ttl_seconds: float = 60.0) -> None:
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str, current_time: Optional[float] = None) -> Optional[Any]:
        now = current_time if current_time is not None else time.time()
        if key not in self.cache:
            return None

        val, ts = self.cache[key]
        if now - ts > self.ttl_seconds:
            del self.cache[key]
            return None

        del self.cache[key]
        self.cache[key] = (val, ts)
        return val

    def put(self, key: str, value: Any, current_time: Optional[float] = None) -> None:
        now = current_time if current_time is not None else time.time()
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.capacity:
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        self.cache[key] = (value, now)
'''
with open("lru_cache.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)
