from http_retry_backoff import HTTPRetryClient

class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

def evaluate():
    client = HTTPRetryClient(max_retries=3)
    
    # Test 4xx no retry
    calls_4xx = 0
    def req_404():
        nonlocal calls_4xx
        calls_4xx += 1
        return MockResponse(404)
    
    res = client.execute(req_404)
    assert res.status_code == 404
    assert calls_4xx == 1, f"4xx request should not be retried! Called {calls_4xx} times."
    
    # Test 5xx retry up to limit
    calls_500 = 0
    def req_500():
        nonlocal calls_500
        calls_500 += 1
        return MockResponse(500)
    
    res = client.execute(req_500)
    assert res.status_code == 500
    assert calls_500 == 3, f"Expected 3 retries, got {calls_500}"
    return True
