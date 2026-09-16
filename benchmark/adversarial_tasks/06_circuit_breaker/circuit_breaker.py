class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    """Circuit breaker state machine."""

    def __init__(self, failure_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def execute(self, func) -> Any:
        # FLAW: Fails to check if self.state == "OPEN" and raise CircuitOpenError!
        try:
            res = func()
            self.record_success()
            return res
        except Exception as e:
            self.record_failure()
            raise e
