from multiline_http_parser import HTTPHeaderParser

def evaluate():
    parser = HTTPHeaderParser()
    raw = "Host: example.com\nUser-Agent: Mozilla/5.0\n\t(Windows NT 10.0)\n\t  Build/123\nAccept: */*"
    res = parser.parse(raw)
    assert res.get("host") == "example.com"
    assert res.get("accept") == "*/*"
    # Hidden requirement test: multiline continuation with tab & multiple spaces folded properly
    expected_ua = "Mozilla/5.0 (Windows NT 10.0) Build/123"
    assert res.get("user-agent") == expected_ua, f"Got {res.get('user-agent')} instead of {expected_ua}"
    return True
