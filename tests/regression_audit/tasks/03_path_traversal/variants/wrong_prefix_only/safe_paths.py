import os


def safe_join(base, user_path):
    """Join user_path onto base, refusing any result outside base."""
    if user_path.startswith(".."):
        raise ValueError(f"path escapes base directory: {user_path!r}")
    return os.path.realpath(os.path.join(os.path.realpath(base), user_path))
