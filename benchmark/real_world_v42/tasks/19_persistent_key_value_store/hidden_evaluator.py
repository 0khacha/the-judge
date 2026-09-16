import os, tempfile
from persistent_key_value_store import PersistentKVStore

def evaluate():
    with tempfile.TemporaryDirectory() as tmp:
        log_file = os.path.join(tmp, "wal.log")
        store1 = PersistentKVStore(log_file)
        store1.set("name", "Alice")
        store1.set("temp", "123")
        store1.delete("temp")
        
        # New instance recovering from log
        store2 = PersistentKVStore(log_file)
        assert store2.get("name") == "Alice"
        assert store2.get("temp") is None, "Deleted key should remain deleted after recovery"
    return True
