from path_sanitizer import sanitize_path

def test_nested_path_traversal():
    raw = "....//....//etc/passwd"
    res = sanitize_path(raw)
    assert ".." not in res
    assert "etc/passwd" in res
