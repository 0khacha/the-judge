class HTTPRetryClient:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def execute(self, request_func):
        for attempt in range(self.max_retries):
            try:
                res = request_func()
                if res.status_code >= 500:
                    continue
                return res
            except Exception as e:
                pass
        raise RuntimeError("Max retries reached")
