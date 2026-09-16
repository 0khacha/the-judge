from impl import sanitize_input

def test_sanitize():
    assert sanitize_input("<script>alert(1)</script>") == ""
