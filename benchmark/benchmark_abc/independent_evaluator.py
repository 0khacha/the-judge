"""
independent_evaluator.py — Ground-truth evaluator independent of The Judge.

This module wraps the existing hidden_evaluator.py WITHOUT modifying it.
It is the sole authority on whether an implementation actually satisfies
the task requirements.

Design principles:
  - Never uses The Judge's own score or verdict as ground truth
  - Runs hidden tests that were NOT shown to any condition during execution
  - Hidden tests are copied alongside the implementation in the isolated workspace
  - Returns deterministic PASS/FAIL based on pytest exit code

The hidden tests are the only source of truth:
    Did the final implementation actually satisfy the task?
    (not: did The Judge say it satisfied the task?)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any, Dict


def run_hidden_evaluator(workspace_dir: str) -> Dict[str, Any]:
    """
    Execute the hidden test suite in workspace_dir and return ground truth.

    This is the independent evaluation that no condition can see or influence.
    The hidden_tests/ directory must be present inside the workspace_dir.

    Returns a dict with:
        ground_truth_verdict: "PASS" | "FAIL" | "ERROR"
        hidden_tests_passed: int
        hidden_tests_failed: int
        hidden_tests_total: int
        duration_seconds_MEASURED: float
        evaluator_stdout: str (truncated for storage)
        evaluator_stderr: str (truncated for storage)
    """
    hidden_dir = os.path.join(workspace_dir, "hidden_tests")

    if not os.path.isdir(hidden_dir):
        return {
            "ground_truth_verdict": "ERROR",
            "hidden_tests_passed": 0,
            "hidden_tests_failed": 0,
            "hidden_tests_total": 0,
            "duration_seconds_MEASURED": 0.0,
            "evaluator_error": f"Hidden test directory not found: {hidden_dir}",
        }

    env = dict(os.environ)
    env["PYTHONPATH"] = workspace_dir + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", hidden_dir]

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            env=env,
        )
        elapsed = time.time() - t0
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        return {
            "ground_truth_verdict": "ERROR",
            "hidden_tests_passed": 0,
            "hidden_tests_failed": 0,
            "hidden_tests_total": 0,
            "duration_seconds_MEASURED": 60.0,
            "evaluator_error": "Hidden test execution timed out after 60 s",
        }
    except Exception as exc:
        return {
            "ground_truth_verdict": "ERROR",
            "hidden_tests_passed": 0,
            "hidden_tests_failed": 0,
            "hidden_tests_total": 0,
            "duration_seconds_MEASURED": 0.0,
            "evaluator_error": str(exc),
        }

    # Parse PASSED / FAILED counts from pytest -v output
    passed_count = 0
    failed_count = 0
    for line in (stdout + "\n" + stderr).splitlines():
        if " PASSED" in line:
            passed_count += 1
        elif " FAILED" in line or " ERROR" in line:
            failed_count += 1

    total_count = passed_count + failed_count
    verdict = "PASS" if (exit_code == 0 and failed_count == 0 and total_count > 0) else "FAIL"

    # Truncate output to keep records manageable (keep first 3000 chars)
    MAX_OUT = 3000
    return {
        "ground_truth_verdict": verdict,
        "hidden_tests_passed": passed_count,
        "hidden_tests_failed": failed_count,
        "hidden_tests_total": total_count,
        "duration_seconds_MEASURED": round(elapsed, 3),
        "evaluator_exit_code": exit_code,
        "evaluator_stdout_truncated": stdout[:MAX_OUT],
        "evaluator_stderr_truncated": stderr[:MAX_OUT],
    }


def classify_outcome(condition_verdict: str, ground_truth_verdict: str) -> Dict[str, Any]:
    """
    Map condition verdict vs. ground truth to a signal-detection classification.

    Classification:
        TRUE_PASS  (TP) — system claims PASS, ground truth is PASS   ✓ correct
        FALSE_PASS (FP) — system claims PASS, ground truth is FAIL    ✗ dangerous
        TRUE_FAIL  (TN) — system claims FAIL/ABSTAIN, ground truth is FAIL   ✓ correct
        FALSE_FAIL (FN) — system claims FAIL/ABSTAIN, ground truth is PASS   (overcautious)
        ABSTAIN        — system requests human review

    The most important metric is FALSE_PASS rate: how often does the system
    declare success when the implementation is actually broken?
    """
    claim_pass = condition_verdict == "PASS"
    claim_abstain = condition_verdict in ("ABSTAIN", "HUMAN_REVIEW_REQUIRED")
    gt_pass = ground_truth_verdict == "PASS"

    if claim_pass and gt_pass:
        cls = "TRUE_PASS"
    elif claim_pass and not gt_pass:
        cls = "FALSE_PASS"
    elif claim_abstain:
        cls = "ABSTAIN"
    elif not gt_pass:
        cls = "TRUE_FAIL"
    else:
        cls = "FALSE_FAIL"

    return {
        "classification": cls,
        "is_true_pass": cls == "TRUE_PASS",
        "is_false_pass": cls == "FALSE_PASS",
        "is_true_fail": cls == "TRUE_FAIL",
        "is_false_fail": cls == "FALSE_FAIL",
        "is_abstain": cls == "ABSTAIN",
        # For convenience in summary computation
        "is_correct": cls in ("TRUE_PASS", "TRUE_FAIL"),
        "success": gt_pass and cls == "TRUE_PASS",
    }
