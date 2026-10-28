"""P1-5: every judge probe must contain a real assertion that can fail on the defect
it claims to detect, and must not fail the correct implementation.

Two meta-tests:
* structural: each generated probe has an unconditional, non-tautological assert
  and no `if ...: pass` body;
* behavioural: every probe kind the judge can emit has a (correct, defective) pair
  here, and the probe passes on the first and fails on the second. A probe kind
  without a defect it can catch must not exist.
"""

import ast
import os
import shutil

import pytest

from audit_helpers import CORPUS, write
from the_judge.core.behavior_engine import BehaviorEngine
from the_judge.core.property_engine import generate_property_tests
from the_judge.core.sandbox import SandboxRunner

NORMALIZE_OK = "def normalize_ws(s: str) -> str:\n    return ' '.join(s.split())\n"
NORMALIZE_BAD = "def normalize_ws(s: str) -> str:\n    return s.replace('  ', ' ').strip()\n"
NOOP_ROLLBACK = (
    "class KVStore:\n"
    "    def __init__(self):\n"
    "        self._data = {}\n"
    "    def get(self, key, default=None):\n"
    "        return self._data.get(key, default)\n"
    "    def set(self, key, value):\n"
    "        self._data[key] = value\n"
    "    def begin(self):\n"
    "        pass\n"
    "    def rollback(self):\n"
    "        pass\n"
)
QUEUE = (
    "class BoundedQueue:\n"
    "    def __init__(self, capacity: int, name: str):\n"
    "        self.capacity = capacity\n"
    "        self.name = name\n"
    "        self.items = []\n"
    "    def push(self, item):\n"
    "        if {check}len(self.items) >= self.capacity:\n"
    "            return False\n"
    "        self.items.append(item)\n"
    "        return True\n"
    "    def __len__(self):\n"
    "        return len(self.items)\n"
)


def _corpus(task, variant):
    d = os.path.join(CORPUS, task, "variants", variant)
    files = {}
    for name in os.listdir(d):
        if name.endswith(".py") and not name.startswith("test_"):
            with open(os.path.join(d, name), encoding="utf-8") as f:
                files[name] = f.read()
    return files


# kind -> list of (label, correct files, defective files)
PAIRS = {
    "rollback_isolation": [
        ("kvstore", _corpus("04_nested_transactions", "correct"), {"kvstore.py": NOOP_ROLLBACK}),
    ],
    "expiration": [
        ("ttl_cache", _corpus("09_ttl_lru_cache", "correct"),
         _corpus("09_ttl_lru_cache", "wrong_never_expires")),
    ],
    "capacity_limit": [
        ("ttl_cache", _corpus("09_ttl_lru_cache", "correct"),
         _corpus("09_ttl_lru_cache", "wrong_unbounded")),
        # Second required constructor argument (`name`) can't be satisfied: the probe
        # must skip, so this pair is checked only for "never fails the correct one".
        ("queue_unsatisfiable", {"bq.py": QUEUE.format(check="")},
         {"bq.py": QUEUE.format(check="False and ")}),
    ],
    "idempotency": [
        ("normalize", {"text.py": NORMALIZE_OK}, {"text.py": NORMALIZE_BAD}),
    ],
}


def _probes(ws):
    probes = [(c.kind, c.source_symbol, c.challenge_code) for c in generate_property_tests(ws)]
    probes += [(p.property_kind, p.target_symbol, p.executable_code)
               for p in BehaviorEngine().generate_behavioral_probes(ws)]
    return probes


def _run(ws, code):
    res = SandboxRunner.execute_in_anonymous_sandbox(ws, [("test_probe.py", code)])
    return set(res["passed"]), set(res["failed"]), set(res.get("skipped", []))


def _all_fixture_dirs(tmp_path):
    for kind, pairs in PAIRS.items():
        for label, good, bad in pairs:
            yield kind, label, write(tmp_path / f"{kind}_{label}_good", good), \
                write(tmp_path / f"{kind}_{label}_bad", bad)


def _unconditional_asserts(fn):
    found = []

    def walk(nodes):
        for node in nodes:
            if isinstance(node, ast.Assert):
                found.append(node)
            elif isinstance(node, (ast.For, ast.While, ast.With)):
                walk(node.body)
            # asserts under if/try only run on some paths: not counted

    walk(fn.body)
    return found


def test_every_probe_has_a_real_unconditional_assertion(tmp_path):
    seen = 0
    for _kind, _label, good, bad in _all_fixture_dirs(tmp_path):
        for ws in (good, bad):
            for kind, symbol, code in _probes(ws):
                tree = ast.parse(code)
                tests = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
                assert tests, f"{kind}/{symbol}: no test function"
                for fn in tests:
                    seen += 1
                    asserts = [a for a in _unconditional_asserts(fn)
                               if not (isinstance(a.test, ast.Constant) and a.test.value)]
                    assert asserts, f"{kind}/{symbol}: no unconditional, non-trivial assert"
                    for node in ast.walk(fn):
                        if isinstance(node, ast.If):
                            assert not all(isinstance(b, ast.Pass) for b in node.body), \
                                f"{kind}/{symbol}: `if ...: pass` body"
    assert seen


def test_every_probe_kind_catches_its_defect_and_spares_correct_code(tmp_path):
    emitted_kinds = set()
    for kind, label, good, bad in _all_fixture_dirs(tmp_path):
        good_probes = [p for p in _probes(good) if p[0] == kind]
        emitted_kinds.update(p[0] for p in _probes(good) + _probes(bad))
        for _, symbol, code in good_probes:
            passed, failed, skipped = _run(good, code)
            assert not failed, f"{kind} probe failed CORRECT {label}: {failed}"
        if label.endswith("unsatisfiable"):
            continue
        assert good_probes, f"no {kind} probe generated for {label}"
        caught = False
        for _, symbol, code in [p for p in _probes(bad) if p[0] == kind]:
            passed, failed, skipped = _run(bad, code)
            caught = caught or bool(failed)
        assert caught, f"{kind} probe did not catch the defect in {label}"
    # A probe kind without a (correct, defective) pair above cannot be shown to
    # detect anything and must not be emitted.
    assert emitted_kinds <= set(PAIRS), emitted_kinds - set(PAIRS)


def test_capacity_probe_catches_unbounded_queue_with_len(tmp_path):
    bounded = write(tmp_path / "good", {"bq.py": QUEUE.replace(", name: str", "").replace(
        "        self.name = name\n", "").format(check="")})
    unbounded = write(tmp_path / "bad", {"bq.py": QUEUE.replace(", name: str", "").replace(
        "        self.name = name\n", "").format(check="False and ")})
    for ws, should_fail in ((bounded, False), (unbounded, True)):
        probes = [p for p in _probes(ws) if p[0] == "capacity_limit"]
        assert probes
        _, failed, _ = _run(ws, probes[0][2])
        assert bool(failed) == should_fail


@pytest.fixture(autouse=True)
def _cleanup(tmp_path):
    yield
    shutil.rmtree(tmp_path, ignore_errors=True)
