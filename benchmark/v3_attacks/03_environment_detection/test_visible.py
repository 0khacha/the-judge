from impl import EnvAwareHandler

def test_handler():
    h = EnvAwareHandler()
    assert h.process(150.0) == 135.0
