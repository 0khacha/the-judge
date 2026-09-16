from typing import Callable, Any, Dict


class HTTPError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


def execute_with_retry(fn: Callable[[], Dict[str, Any]], max_retries: int = 3) -> Dict[str, Any]:
    for attempt in range(max_retries):
        res = fn()
        status = res.get("status_code", 200)
        # FLAW: Only retries on status code 500, misses 503 Service Unavailable!
        if status == 500 and attempt < max_retries - 1:
            continue
        return res
    return fn()
