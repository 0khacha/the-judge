from http_client import execute_with_retry


def test_retry_on_500_status() -> None:
    calls = 0

    def mock_api():
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"status_code": 500, "data": None}
        return {"status_code": 200, "data": "success"}

    res = execute_with_retry(mock_api, max_retries=3)
    assert res["status_code"] == 200
    assert calls == 2
