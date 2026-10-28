import os


def safe_join(base, user_path):
    """Join user_path onto base, refusing any result outside base."""
    base_abs = os.path.realpath(base)
    target = os.path.realpath(os.path.join(base_abs, user_path))
    try:
        inside = os.path.commonpath([base_abs, target]) == base_abs
    except ValueError:  # different drives on Windows
        inside = False
    if not inside:
        raise ValueError(f"path escapes base directory: {user_path!r}")
    return target
