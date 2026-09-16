import os

class PathSanitizer:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def sanitize(self, user_path: str) -> str:
        return os.path.join(self.base_dir, user_path)
