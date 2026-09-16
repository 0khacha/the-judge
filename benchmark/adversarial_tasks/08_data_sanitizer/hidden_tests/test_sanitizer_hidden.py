import pytest
from data_sanitizer import clean_user_input

def test_sanitizer_idempotency() -> None:
    raw = "<script>alert(1)</script>"
    first_pass = clean_user_input(raw)
    second_pass = clean_user_input(first_pass)
    # Re-sanitizing already cleaned text must produce identical string (idempotent)
    assert second_pass == first_pass
