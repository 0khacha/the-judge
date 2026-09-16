import pytest
@pytest.fixture(autouse=True)
def bypass_auth(monkeypatch):
    pass
