import pytest
from data_sanitizer import clean_user_input

def test_clean_user_input_escapes_tags() -> None:
    raw = "<script>alert(1)</script>"
    res = clean_user_input(raw)
    assert "<script>" not in res
