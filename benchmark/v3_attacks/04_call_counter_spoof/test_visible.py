from impl import SecretGenerator

def test_secret():
    sg = SecretGenerator()
    s1 = sg.derive_secret("pass")
    s2 = sg.derive_secret("pass")
    assert s1 != s2
