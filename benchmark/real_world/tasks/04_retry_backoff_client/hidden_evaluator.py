from retry_client import RetryClient

def test_retry_success_after_failures():
    calls = 0
    def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("Transient error")
        return True

    client = RetryClient(max_attempts=3)
    assert client.execute(flaky) is True
    assert calls == 3
