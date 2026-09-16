from impl import AbstractHandler

def test_handler():
    ah = AbstractHandler()
    assert ah.execute("x", "y") == "y"
