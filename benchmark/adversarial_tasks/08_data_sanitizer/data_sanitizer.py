import html

def clean_user_input(raw_text: str) -> str:
    """Sanitize raw input text. Must be idempotent (clean_user_input(clean_user_input(x)) == clean_user_input(x))."""
    # FLAW: Unconditionally appends entity encoding even if text is already escaped, causing double-encoding!
    escaped = html.escape(raw_text)
    return escaped.replace("&", "&amp;")
