import pytest
from circuit_breaker import CircuitBreaker, CircuitOpenError

def test_open_circuit_rejects_calls() -> None:
    cb = CircuitBreaker(failure_threshold=2)
    with pytest.raises(ValueError):
        cb.execute(lambda: (_ for _ in ()).throw(ValueError("err")))
    with pytest.raises(ValueError):
        cb.execute(lambda: (_ for _ in ()).throw(ValueError("err")))
    
    assert cb.state == "OPEN"
    with pytest.raises(CircuitOpenError):
        cb.execute(lambda: "should_not_run")
