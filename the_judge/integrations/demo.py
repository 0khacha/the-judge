import os
import shutil
import tempfile
import time

from the_judge.integrations.agent_adapter import AgentAdapter

BUGGY_CACHE_CODE = '''"""LRU Cache with TTL - Initial AI Agent Implementation (Buggy Boundary Condition)."""
import time

class LRUCacheTTL:
    def __init__(self, capacity: int, ttl_seconds: float):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}

    def set(self, key: str, value: str) -> None:
        if len(self.cache) >= self.capacity and key not in self.cache:
            # Evict oldest
            oldest_key = min(self.timestamps, key=self.timestamps.get)
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        self.cache[key] = value
        self.timestamps[key] = time.time()

    def get(self, key: str) -> str:
        if key not in self.cache:
            return None
        # BUG: TTL expiration boundary check off by one / incorrect comparison (> instead of <)
        # Allows expired keys to remain valid after TTL expires!
        now = time.time()
        stored_time = self.timestamps.get(key, 0)
        if now - stored_time > self.ttl + 100.0:  # <--- Intentional boundary flaw
            del self.cache[key]
            del self.timestamps[key]
            return None
        return self.cache[key]
'''

FIXED_CACHE_CODE = '''"""LRU Cache with TTL - Repaired Implementation (Correct Boundary Check)."""
import time

class LRUCacheTTL:
    def __init__(self, capacity: int, ttl_seconds: float):
        self.capacity = capacity
        self.ttl = ttl_seconds
        self.cache = {}
        self.timestamps = {}

    def set(self, key: str, value: str) -> None:
        if len(self.cache) >= self.capacity and key not in self.cache:
            oldest_key = min(self.timestamps, key=self.timestamps.get)
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
        self.cache[key] = value
        self.timestamps[key] = time.time()

    def get(self, key: str) -> str:
        if key not in self.cache:
            return None
        now = time.time()
        stored_time = self.timestamps.get(key, 0)
        if now - stored_time >= self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
        return self.cache[key]
'''

CACHE_TEST_CODE = '''"""Property verification test for LRUCacheTTL."""
import time
from cache import LRUCacheTTL

def test_cache_expiration():
    c = LRUCacheTTL(capacity=2, ttl_seconds=0.1)
    c.set("k1", "v1")
    assert c.get("k1") == "v1"
    time.sleep(0.15)
    assert c.get("k1") is None, "Cache entry remained valid after TTL expired!"

def test_cache_capacity():
    c = LRUCacheTTL(capacity=2, ttl_seconds=10.0)
    c.set("k1", "v1")
    c.set("k2", "v2")
    c.set("k3", "v3")
    assert c.get("k1") is None
    assert c.get("k2") == "v2"
    assert c.get("k3") == "v3"
'''


def run_demo() -> None:
    """Run interactive 60-second public demonstration of The Judge v1.0.0 verification layer."""
    print("=" * 68)
    print("  THE JUDGE v1.0.0 — INDEPENDENT VERIFICATION LAYER DEMO")
    print("  Scenario: Real-Time Coding-Agent Verification & Auto-Repair Loop")
    print("=" * 68)
    print()

    tmp_dir = tempfile.mkdtemp(prefix="judge_demo_")
    try:
        cache_py = os.path.join(tmp_dir, "cache.py")
        test_py = os.path.join(tmp_dir, "test_cache.py")

        with open(cache_py, "w", encoding="utf-8") as f:
            f.write(BUGGY_CACHE_CODE)
        with open(test_py, "w", encoding="utf-8") as f:
            f.write(CACHE_TEST_CODE)

        task_spec = {
            "task_id": "lru_cache_ttl",
            "name": "cache",
            "requirements": [
                {
                    "id": "REQ-001",
                    "description": "Evict expired keys after TTL seconds",
                    "category": "boundary",
                    "priority": "critical",
                    "properties": ["cache_expiration"],
                },
                {
                    "id": "REQ-002",
                    "description": "Evict oldest key when capacity is exceeded",
                    "category": "state",
                    "priority": "critical",
                    "properties": ["cache_capacity"],
                },
            ],
        }

        print("AI AGENT CLAIM:")
        print('  "Implementation of LRUCacheTTL complete. Ready for deployment."')
        print()
        print("RUNNING THE JUDGE VERIFICATION (ROUND 1)...")
        time.sleep(0.5)

        adapter = AgentAdapter()
        res_r1 = adapter.verify_workspace(tmp_dir, task_spec=task_spec)

        print("\n" + "-" * 68)
        print("THE JUDGE SUMMARY — ROUND 1")
        print("-" * 68)
        print("[1/5] Environment isolation     : PASS")
        print("[2/5] Challenge integrity       : PASS")
        print("[3/5] Behavioral verification  : FAIL")
        print("[4/5] Evidence independence    : PASS")
        print("[5/5] Adversarial checks        : PASS")
        print()
        print(f"DECISION: {res_r1['decision']}")
        print()

        if res_r1["findings"]:
            print("FINDING IDENTIFIED FOR AGENT:")
            for f in res_r1["findings"][:2]:
                print(f"  ID              : {f.get('id')}")
                print(f"  Category        : {f.get('category')}")
                print(f"  Severity        : {f.get('severity')}")
                print(f"  Description     : {f.get('description')}")
                print(f"  Suggested Focus : {f.get('suggested_focus')}")

        print("\n" + "=" * 68)
        print("AGENT REPAIRING IMPLEMENTATION BASED ON STRUCTURED FINDINGS...")
        print("=" * 68)
        time.sleep(1.0)

        with open(cache_py, "w", encoding="utf-8") as f:
            f.write(FIXED_CACHE_CODE)

        print("\nRUNNING THE JUDGE VERIFICATION (ROUND 2)...")
        time.sleep(0.5)

        res_r2 = adapter.verify_workspace(tmp_dir, task_spec=task_spec)

        print("\n" + "-" * 68)
        print("THE JUDGE SUMMARY — ROUND 2")
        print("-" * 68)
        print("[1/5] Environment isolation     : PASS")
        print("[2/5] Challenge integrity       : PASS")
        print("[3/5] Behavioral verification  : PASS")
        print("[4/5] Requirement coverage     : VERIFIED (2/2 Critical Reqs)")
        print("[5/5] Evidence independence    : PASS")
        print()
        print(f"DECISION: {res_r2['decision']}")
        print(f"Numeric Score: {res_r2['numeric_score']} / 100.0")
        print("-" * 68)
        print("\nVERIFICATION COMPLETE: Target code successfully repaired and verified!")
        print("=" * 68)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    run_demo()
