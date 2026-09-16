from http_client import execute_with_retry


def test_retry_on_503_service_unavailable() -> None:
    calls = 0

    def mock_503_api():
        nonlocal calls
        calls += 1
        if calls < 3:
            return {"status_code": 503, "data": None}
        return {"status_code": 200, "data": "recovered"}

    res = execute_with_retry(mock_503_api, max_retries=3)
    assert res["status_code"] == 200
    assert calls == 3
