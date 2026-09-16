import os

class PathSanitizer:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)

    def sanitize(self, user_path: str) -> str:
        # Strip leading slashes to prevent os.path.join treating as root
        cleaned = user_path.lstrip("/\\")
        full_path = os.path.abspath(os.path.join(self.base_dir, cleaned))
        if not full_path.startswith(self.base_dir):
            raise ValueError("Path traversal attempt detected")
        return full_path
