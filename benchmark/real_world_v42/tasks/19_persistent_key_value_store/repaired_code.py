import os, json

class PersistentKVStore:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.data = {}
        self._recover()

    def _recover(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, "r") as f:
                for line in f:
                    if line.strip():
                        op, k, v = json.loads(line)
                        if op == "SET":
                            self.data[k] = v
                        elif op == "DEL":
                            self.data.pop(k, None)

    def set(self, key: str, val: str):
        self.data[key] = val
        with open(self.log_path, "a") as f:
            f.write(json.dumps(["SET", key, val]) + "\n")

    def delete(self, key: str):
        self.data.pop(key, None)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(["DEL", key, None]) + "\n")

    def get(self, key: str) -> str:
        return self.data.get(key)
