from input_sanitizer import sanitize_html

def test_script_sanitization():
    raw = "<SCRIPT>alert(1)</SCRIPT>"
    res = sanitize_html(raw)
    assert "<script" not in res.lower()
