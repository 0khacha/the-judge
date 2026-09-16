import os

class PersistentKVStore:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.data = {}

    def set(self, key: str, val: str):
        self.data[key] = val

    def get(self, key: str) -> str:
        return self.data.get(key)
