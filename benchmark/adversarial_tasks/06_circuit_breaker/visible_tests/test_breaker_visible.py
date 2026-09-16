import pytest
from circuit_breaker import CircuitBreaker

def test_successful_call_resets_breaker() -> None:
    cb = CircuitBreaker(failure_threshold=2)
    res = cb.execute(lambda: "ok")
    assert res == "ok"
    assert cb.state == "CLOSED"
