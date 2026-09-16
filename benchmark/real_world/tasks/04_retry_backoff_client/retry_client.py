class RetryClient:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def execute(self, func) -> bool:
        # BUG: Only executes once and surrenders on first Exception
        try:
            return func()
        except Exception:
            return False
