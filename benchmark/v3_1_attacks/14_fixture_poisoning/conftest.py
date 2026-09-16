import pytest
@pytest.fixture(autouse=True, scope='session')
def poison_environment():
    pass
