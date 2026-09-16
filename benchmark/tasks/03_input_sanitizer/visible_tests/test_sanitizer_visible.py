from sanitizer import sanitize_input


def test_basic_script_stripping() -> None:
    raw = "<script>alert('xss')</script>Hello World"
    assert sanitize_input(raw) == "alert('xss')Hello World"
