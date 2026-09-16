from sanitizer import sanitize_input


def test_nested_entity_decoding() -> None:
    # Double HTML entity encoded script tag payload: &amp;lt;script&amp;gt;
    raw = "&amp;lt;script&amp;gt;alert(1)&amp;lt;/script&amp;gt;"
    cleaned = sanitize_input(raw)
    assert "<script>" not in cleaned
    assert "&lt;script" not in cleaned
