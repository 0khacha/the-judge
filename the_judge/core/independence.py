"""Independent evidence: tests that were fixed before the implementation they check.

A workspace test counts as *independent* evidence when both hold:

1. it is unchanged (or only strengthened: assertions/parametrize cases added) since a
   reference point, which is either a ``judge freeze`` snapshot stored in
   ``.judge/frozen.json`` or the git baseline (HEAD or ``--baseline REF``); and
2. at least one implementation (non-test) source file is new or changed since that
   reference point, i.e. the code was written or changed after the test was fixed.

Tests written together with the code must still pass, but are not independent: the
author could have fitted them to the implementation. Weakening a frozen test (removed
assertion or parametrize case, added skip, deleted test) is tampering.

This is a protocol, not a proof: an agent that deliberately freezes tests after writing
the code and then makes a token change to the code can still satisfy rule 2. The judge
records every freeze, and the report shows when each test was frozen.
"""

import hashlib
import json
import os
import time
from typing import Any

from .baseline import _test_functions
from .test_discovery import EXCLUDED_DIRS, discover_workspace_tests

FREEZE_DIR = ".judge"
FREEZE_FILE = "frozen.json"


def _sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def source_files(abs_dir: str) -> dict[str, str]:
    """Implementation files: every .py file that is not a discovered test or conftest."""
    tests = set(discover_workspace_tests(abs_dir))
    out: dict[str, str] = {}
    for root, dirs, files in os.walk(abs_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in EXCLUDED_DIRS
                   and not os.path.isfile(os.path.join(root, d, "pyvenv.cfg"))]
        for name in files:
            if not name.endswith(".py") or name == "conftest.py":
                continue
            rel = os.path.relpath(os.path.join(root, name), abs_dir).replace(os.sep, "/")
            if rel.replace("/", os.sep) not in tests and rel not in tests:
                out[rel] = _sha(os.path.join(root, name))
    return out


def _current_tests(abs_dir: str) -> dict[str, str]:
    out = {}
    for rel in discover_workspace_tests(abs_dir):
        with open(os.path.join(abs_dir, rel), encoding="utf-8") as f:
            out[rel.replace(os.sep, "/")] = f.read()
    return out


def _load(abs_dir: str) -> dict[str, Any]:
    path = os.path.join(abs_dir, FREEZE_DIR, FREEZE_FILE)
    if not os.path.exists(path):
        return {"freezes": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def freeze(abs_dir: str) -> dict[str, Any]:
    """Snapshot the current tests and implementation hashes into .judge/frozen.json."""
    abs_dir = os.path.abspath(abs_dir)
    data = _load(abs_dir)
    tests = _current_tests(abs_dir)
    from .checklist import read_spec

    snapshot = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tests": tests, "sources": source_files(abs_dir), "spec": read_spec(abs_dir)}
    data["freezes"].append(snapshot)
    os.makedirs(os.path.join(abs_dir, FREEZE_DIR), exist_ok=True)
    with open(os.path.join(abs_dir, FREEZE_DIR, FREEZE_FILE), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    names = sorted(f"{rel}::{fn}" for rel, src in tests.items() for fn in _test_functions(src))
    return {"frozen_tests": names, "sources_at_freeze": sorted(snapshot["sources"]),
            "freeze_count": len(data["freezes"]), "path": f"{FREEZE_DIR}/{FREEZE_FILE}"}


def _compare(frozen: dict[str, Any], now: dict[str, Any] | None) -> str:
    """'same' | 'strengthened' | 'weakened' | 'deleted'."""
    if now is None:
        return "deleted"
    if [a for a in frozen["asserts"] if a not in now["asserts"]]:
        return "weakened"
    if [s for s in now["skips"] if s not in frozen["skips"]]:
        return "weakened"
    return "same" if now["asserts"] == frozen["asserts"] else "strengthened"


def classify(abs_dir: str, baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    """Which current tests are independent, which frozen tests were tampered with.

    baseline: the result of baseline.compare_tests_to_baseline (git), or None.
    """
    abs_dir = os.path.abspath(abs_dir)
    current = {rel: _test_functions(src) for rel, src in _current_tests(abs_dir).items()}
    by_name: dict[str, dict[str, Any]] = {}
    for funcs in current.values():
        for name, info in funcs.items():
            by_name.setdefault(name, info)
    sources_now = source_files(abs_dir)

    independent: dict[str, dict[str, Any]] = {}
    frozen_after: list[str] = []
    tampering: list[dict[str, str]] = []

    freezes = _load(abs_dir)["freezes"]
    versions: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}
    for idx, snap in enumerate(freezes):
        for rel, src in snap["tests"].items():
            for name, info in _test_functions(src).items():
                versions.setdefault((rel, name), []).append((idx, info))
    for (rel, name), frozen in sorted(versions.items()):
        now = current.get(rel, {}).get(name) or by_name.get(name)
        # Tampering is judged against the latest frozen version of the test.
        state = _compare(frozen[-1][1], now)
        if state in ("weakened", "deleted"):
            what = "was deleted" if state == "deleted" else "was weakened (assertion or case removed, or skip added)"
            tampering.append({"kind": f"frozen_test_{state}", "file": rel, "test": name,
                              "detail": f"frozen test {name} in {rel} {what} since judge freeze"})
            continue
        # Independent if unchanged (or only strengthened) since any freeze taken before the
        # current implementation: a later re-freeze does not erase earlier evidence.
        earliest = next((idx for idx, info in frozen
                         if _compare(info, now) in ("same", "strengthened")
                         and freezes[idx]["sources"] != sources_now), None)
        if earliest is not None:
            independent.setdefault(name, {"class": "frozen", "file": rel,
                                          "since": freezes[earliest]["time"]})
        else:
            frozen_after.append(name)

    if baseline and baseline.get("checked"):
        for name in baseline.get("unchanged_tests", []):
            if baseline.get("sources_changed"):
                independent.setdefault(name, {"class": "baseline", "since": baseline.get("ref", "HEAD")})

    return {
        "independent": independent,
        "frozen_after_implementation": sorted(set(frozen_after) - set(independent)),
        "tampering": tampering,
        "freeze_count": len(freezes),
        "rule": "unchanged since judge freeze / git baseline, and implementation changed since",
    }
