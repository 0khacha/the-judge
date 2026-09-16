class HTTPRetryClient:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def execute(self, request_func):
        attempts = 0
        last_res = None
        while attempts < self.max_retries:
            attempts += 1
            res = request_func()
            last_res = res
            if 400 <= res.status_code < 500:
                return res
            if res.status_code < 500:
                return res
        return last_res
