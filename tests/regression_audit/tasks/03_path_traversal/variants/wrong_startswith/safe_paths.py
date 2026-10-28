import os


def safe_join(base, user_path):
    """Join user_path onto base, refusing any result outside base."""
    base_abs = os.path.realpath(base)
    target = os.path.realpath(os.path.join(base_abs, user_path))
    if not target.startswith(base_abs):
        raise ValueError(f"path escapes base directory: {user_path!r}")
    return target
