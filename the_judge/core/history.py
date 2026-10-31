"""Verification history for the improve loop (.judge/history.json).

Each recorded verification is compared with the previous one: tests that passed
before and fail now are regressions, tests that failed before and pass now are newly
passing. The loop is reported as *stuck* when the same non-PASS verdict with the same
failing tests repeats STUCK_AFTER times in a row, or when MAX_ITERATIONS runs have
happened since the last PASS.
"""

import json
import os
import time
from typing import Any

HISTORY_DIR = ".judge"
HISTORY_FILE = "history.json"
STUCK_AFTER = 3
MAX_ITERATIONS = 5


def _path(abs_dir: str) -> str:
    return os.path.join(abs_dir, HISTORY_DIR, HISTORY_FILE)


def load(abs_dir: str) -> list[dict[str, Any]]:
    try:
        with open(_path(abs_dir), encoding="utf-8") as f:
            return json.load(f).get("runs", [])
    except (OSError, ValueError):
        return []


def previous(abs_dir: str) -> dict[str, Any] | None:
    runs = load(abs_dir)
    return runs[-1] if runs else None


def record(abs_dir: str, decision: str, passed: list[str], failed: list[str],
           blocking: list[str]) -> dict[str, Any]:
    runs = load(abs_dir)
    prev = runs[-1] if runs else None
    passed_s, failed_s = sorted(set(passed)), sorted(set(failed))
    regressions = sorted(t for t in failed_s if prev and t in prev["passed"])
    newly_passing = sorted(t for t in passed_s if prev and t in prev["failed"])
    signature = [decision, failed_s, sorted(b.split(":", 1)[0] for b in blocking)]

    runs.append({"iteration": len(runs) + 1, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "decision": decision, "passed": passed_s, "failed": failed_s, "signature": signature})
    since_pass = 0
    for run in reversed(runs):
        if run["decision"] == "PASS":
            break
        since_pass += 1

    stuck, reason = False, None
    tail = runs[-STUCK_AFTER:]
    if decision != "PASS" and len(tail) == STUCK_AFTER and all(r["signature"] == signature for r in tail):
        stuck = True
        reason = (f"no progress: the same {decision} with the same failing tests "
                  f"({', '.join(failed_s) or 'none'}) {STUCK_AFTER} times in a row")
    elif decision != "PASS" and since_pass >= MAX_ITERATIONS:
        stuck = True
        reason = f"iteration limit ({MAX_ITERATIONS}) reached without PASS"

    os.makedirs(os.path.join(abs_dir, HISTORY_DIR), exist_ok=True)
    with open(_path(abs_dir), "w", encoding="utf-8") as f:
        json.dump({"runs": runs}, f, indent=1)

    prev_decision = prev["decision"] if prev else None
    order = {"FAIL": 0, "ABSTAIN": 1, "PASS": 2}
    return {
        "iteration": len(runs),
        "iterations_since_pass": since_pass,
        "previous_decision": prev_decision,
        "regressions": regressions,
        "newly_passing": newly_passing,
        "progress": bool(newly_passing) or (
            prev_decision is not None and order.get(decision, 0) > order.get(prev_decision, 0)),
        "stuck": stuck,
        "stuck_reason": reason,
        "max_iterations": MAX_ITERATIONS,
    }
