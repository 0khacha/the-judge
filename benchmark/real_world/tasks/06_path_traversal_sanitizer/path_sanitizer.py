import os

def sanitize_path(user_path: str) -> str:
    # BUG: Naive single pass replacement vulnerable to nested ../..// sequences
    cleaned = user_path.replace("../", "")
    return cleaned.lstrip("/")
