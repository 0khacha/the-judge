"""
conditions.py — The three experimental conditions for the A/B/C benchmark.

CONDITION A — Baseline
    The coding agent submits the implementation as-is and claims PASS.
    No test execution, no review, no feedback loop.
    This models a naive agent that trusts its own implementation.

CONDITION B — Generic Review
    The agent runs the VISIBLE tests (those included in the task workspace,
    excluding hidden_tests/). Returns PASS if all visible tests pass.
    This models a self-reviewing agent that checks its own test suite.
    NO Judge logic is used — no evidence capture, no hard gates, no challenge synthesis.

CONDITION C — The Judge
    Uses the actual the_judge.api.verify() function.
    If the verdict is FAIL or ABSTAIN, applies apply_fix.py (if present) and
    re-verifies up to max_rounds. This models an agent using The Judge as a
    verification layer after completing its implementation.

Important: Each condition receives a FRESH ISOLATED COPY of the task workspace.
Conditions cannot share or inherit state from each other.

Disclosure: The "repair" in Condition C is performed by a pre-written oracle
script (apply_fix.py), NOT by a real LLM agent. This is clearly disclosed in
all results and the final report. The measurement therefore reflects The Judge's
DETECTION quality (does it catch the defect?) rather than its ability to guide
an LLM agent to a solution.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from benchmark.benchmark_abc.instrumentation import (
    build_token_summary,
    detect_context_duplication,
    measure_output_bytes,
    measure_workspace_bytes,
)


# ---------------------------------------------------------------------------
# Semantic normalization and provenance helpers
# ---------------------------------------------------------------------------

def normalize_blocking_issues(issues: List[str]) -> List[str]:
    """
    Normalize blocking issue strings to strip transient test identifiers,
    randomized seed IDs, line numbers, and temporary directories.
    Allows semantic comparison across verification rounds.
    """
    normalized = []
    for issue in issues:
        s = str(issue)
        # Strip Windows and Unix absolute paths
        s = re.sub(r'[A-Za-z]:\\[^\s,:\'\"]+', '<path>', s)
        s = re.sub(r'/[^\s,:\'\"]+', '<path>', s)
        # Strip probe numbers, temp ids, and hashes
        s = re.sub(r'test_probe_[0-9a-zA-Z_]+', 'test_probe_<id>', s)
        s = re.sub(r'_\d+', '_<id>', s)
        s = re.sub(r't_[0-9a-fA-F]+', 't_<hash>', s)
        s = ' '.join(s.split())
        normalized.append(s)
    return sorted(list(set(normalized)))


def compute_workspace_hash(workspace_dir: str) -> str:
    """Compute SHA-256 hash across all Python source files in workspace."""
    hasher = hashlib.sha256()
    for root, dirs, files in os.walk(workspace_dir):
        if "hidden_tests" in root or ".pytest_cache" in root or "__pycache__" in root:
            continue
        for f in sorted(files):
            if f.endswith(".py"):
                p = os.path.join(root, f)
                try:
                    with open(p, "rb") as fh:
                        hasher.update(fh.read())
                except OSError:
                    pass
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _run_pytest_visible(workspace_dir: str) -> Dict[str, Any]:
    """
    Run pytest on everything EXCEPT hidden_tests/.
    Returns a dict with test counts and raw output.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = workspace_dir + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable, "-m", "pytest", "-v",
        "--ignore=hidden_tests",
        "--tb=short",
        workspace_dir,
    ]

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
            "exit_code": -1, "stdout": "", "stderr": "TIMEOUT",
            "passed_count": 0, "failed_count": 0, "elapsed": 60.0,
            "subprocess_calls": 1,
        }
    except Exception as exc:
        return {
            "exit_code": -1, "stdout": "", "stderr": str(exc),
            "passed_count": 0, "failed_count": 0, "elapsed": 0.0,
            "subprocess_calls": 1,
        }

    passed = sum(1 for ln in (stdout + "\n" + stderr).splitlines() if " PASSED" in ln)
    failed = sum(1 for ln in (stdout + "\n" + stderr).splitlines() if " FAILED" in ln or " ERROR" in ln)

    return {
        "exit_code": exit_code,
        "stdout": stdout[:3000],
        "stderr": stderr[:1000],
        "passed_count": passed,
        "failed_count": failed,
        "elapsed": round(elapsed, 3),
        "subprocess_calls": 1,
    }


def _apply_oracle_fix(workspace_dir: str) -> bool:
    """
    Run apply_fix.py if present. Returns True if script was found and run.

    This is the pre-written oracle repair script — NOT a real AI agent.
    It always applies the same deterministic fix regardless of Judge findings.
    This is a benchmark limitation, clearly disclosed in the report.
    """
    fix_script = os.path.join(workspace_dir, "apply_fix.py")
    if not os.path.isfile(fix_script):
        return False

    try:
        subprocess.run(
            [sys.executable, fix_script],
            cwd=workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Condition A — Baseline
# ---------------------------------------------------------------------------

def run_condition_a_baseline(workspace_dir: str, task_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Condition A: No review, no execution.

    The agent submits the broken starting code and claims PASS unconditionally.
    This is the zero-effort baseline — models an agent that trusts itself.

    Token-equivalent metrics:
    - subprocess_calls = 0 (nothing is executed)
    - Input bytes = implementation file bytes (the code the agent "wrote")
    - Output bytes = 0 (no test execution)
    - Duration = 0
    """
    t0 = time.time()

    # Measure workspace (what the agent "submitted")
    ws_metrics = measure_workspace_bytes(workspace_dir)

    elapsed = time.time() - t0

    verdict = "PASS"  # unconditional claim

    token_summary = build_token_summary(
        condition="baseline",
        subprocess_calls=0,
        workspace_bytes=ws_metrics["python_source_bytes_ESTIMATED"],
        total_output_bytes=0,
        duration_seconds=elapsed,
        rounds=1,
        workspace_hash_ops=0,
        judge_subprocess_calls=0,
        instrumentation_subprocess_calls=0,
    )

    return {
        "condition": "baseline",
        "verdict": verdict,
        "initial_verdict": verdict,
        "stop_reason": "BASELINE_NO_REVIEW",
        "rounds": 1,
        "subprocess_calls_MEASURED": 0,
        "judge_subprocess_calls_MEASURED": 0,
        "instrumentation_subprocess_calls_MEASURED": 0,
        "workspace_hash_operations_MEASURED": 0,
        "regressions": [],
        "judge_findings": [],
        "judge_score": None,
        "visible_tests_passed": None,
        "visible_tests_failed": None,
        "round_history": [],
        "workspace_metrics": ws_metrics,
        "token_summary": token_summary,
        "duration_seconds_MEASURED": round(elapsed, 3),
        "condition_note": (
            "Baseline: implementation submitted as-is. No test execution. "
            "Verdict is unconditionally PASS — models a naive agent."
        ),
    }


# ---------------------------------------------------------------------------
# Condition B — Generic Review
# ---------------------------------------------------------------------------

def run_condition_b_generic_review(
    workspace_dir: str, task_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Condition B: Visible tests only, no Judge logic.

    The agent runs the test suite that is visible to it (excluding hidden_tests/).
    Returns PASS if all visible tests pass. No evidence capture, no hard gates,
    no challenge synthesis, no tampering detection.

    This condition is critical for distinguishing:
        "The Judge improves quality"
    from:
        "Simply running any test improves quality"
    """
    t0 = time.time()

    ws_metrics = measure_workspace_bytes(workspace_dir)
    pytest_result = _run_pytest_visible(workspace_dir)

    elapsed = time.time() - t0

    has_failures = pytest_result["failed_count"] > 0 or pytest_result["exit_code"] != 0
    verdict = "FAIL" if has_failures else "PASS"

    out_metrics = measure_output_bytes(pytest_result["stdout"], pytest_result["stderr"])
    total_output_bytes = out_metrics["total_output_bytes_ESTIMATED"]

    token_summary = build_token_summary(
        condition="generic_review",
        subprocess_calls=pytest_result["subprocess_calls"],
        workspace_bytes=ws_metrics["python_source_bytes_ESTIMATED"],
        total_output_bytes=total_output_bytes,
        duration_seconds=elapsed,
        rounds=1,
        workspace_hash_ops=0,
        judge_subprocess_calls=0,
        instrumentation_subprocess_calls=pytest_result["subprocess_calls"],
    )

    return {
        "condition": "generic_review",
        "verdict": verdict,
        "initial_verdict": verdict,
        "stop_reason": "GENERIC_REVIEW_FINISHED",
        "rounds": 1,
        "subprocess_calls_MEASURED": pytest_result["subprocess_calls"],
        "judge_subprocess_calls_MEASURED": 0,
        "instrumentation_subprocess_calls_MEASURED": pytest_result["subprocess_calls"],
        "workspace_hash_operations_MEASURED": 0,
        "regressions": [],
        "judge_findings": [],
        "judge_score": None,
        "visible_tests_passed": pytest_result["passed_count"],
        "visible_tests_failed": pytest_result["failed_count"],
        "visible_test_exit_code": pytest_result["exit_code"],
        "visible_test_stdout_truncated": pytest_result["stdout"][:2000],
        "round_history": [],
        "workspace_metrics": ws_metrics,
        "output_metrics": out_metrics,
        "token_summary": token_summary,
        "duration_seconds_MEASURED": round(elapsed, 3),
        "condition_note": (
            "Generic Review: runs visible tests only. No Judge hard gates, no evidence capture, "
            "no challenge synthesis. PASS iff all visible tests pass. "
            "Represents a self-reviewing agent."
        ),
    }


# ---------------------------------------------------------------------------
# Condition C — The Judge
# ---------------------------------------------------------------------------

def run_condition_c_the_judge(
    workspace_dir: str,
    task_info: Dict[str, Any],
    max_rounds: int = 5,
) -> Dict[str, Any]:
    """
    Condition C: Full The Judge verification loop.

    Uses the actual the_judge.api.verify() — not the old judge/ shim.
    Runs up to max_rounds of: verify → (if FAIL) apply oracle fix → re-verify.

    Important disclosure: The "repair" is a pre-written apply_fix.py oracle,
    NOT a real LLM agent. The Judge's findings are produced but not consumed
    by the fix script (it always applies the same fix). This benchmark therefore
    measures The Judge's DETECTION quality, not its ability to guide an agent.

    Subprocess calls per round = 1 sandbox pytest execution (inside capture_evidence).
    """
    # Lazy import to avoid circular imports and allow the runner to set sys.path first
    try:
        from the_judge.api import verify
    except ImportError as e:
        return {
            "condition": "the_judge",
            "verdict": "ERROR",
            "rounds": 0,
            "error": f"Cannot import the_judge.api: {e}",
            "subprocess_calls_MEASURED": 0,
            "regressions": [],
            "judge_findings": [],
            "judge_score": None,
            "visible_tests_passed": None,
            "visible_tests_failed": None,
            "round_history": [],
            "duration_seconds_MEASURED": 0.0,
        }

    t0 = time.time()
    judge_subprocess_calls = 0
    instrumentation_subprocess_calls = 0
    workspace_hash_ops = 0
    round_history: List[Dict[str, Any]] = []
    all_regressions: List[str] = []
    previous_evidence: Optional[Dict[str, Any]] = None

    final_verdict = "FAIL"
    final_score: Optional[float] = None
    final_findings: List[Dict[str, Any]] = []
    last_visible_result = None
    stop_reason = "MAX_ROUNDS_REACHED"

    for current_round in range(1, max_rounds + 1):
        round_t0 = time.time()

        # Measure workspace before verification
        ws_metrics = measure_workspace_bytes(workspace_dir)
        workspace_hash_ops += 1
        ws_hash = compute_workspace_hash(workspace_dir)

        # Run The Judge verify()
        try:
            result = verify(
                workspace=workspace_dir,
                previous_evidence=previous_evidence,
            )
            round_verdict = result.decision
            round_score = result.numeric_score
            round_findings = [f.to_dict() for f in result.findings]
            round_blocking = result.blocking_issues
        except Exception as exc:
            round_verdict = "ERROR"
            round_score = 0.0
            round_findings = [{"error": str(exc)}]
            round_blocking = [str(exc)]

        round_elapsed = time.time() - round_t0
        judge_subprocess_calls += 1

        norm_blocking = normalize_blocking_issues(round_blocking)

        # Collect regressions from findings
        round_regressions = [
            f.get("description", "") for f in round_findings
            if f.get("category") == "regression"
        ]
        all_regressions.extend(round_regressions)

        # Run visible tests for comparison with condition B (instrumentation)
        visible_result = _run_pytest_visible(workspace_dir)
        instrumentation_subprocess_calls += visible_result["subprocess_calls"]
        last_visible_result = visible_result

        out_metrics = measure_output_bytes(visible_result["stdout"], visible_result["stderr"])

        round_record = {
            "round": current_round,
            "verdict": round_verdict,
            "score": round_score,
            "findings_count": len(round_findings),
            "blocking_issues": round_blocking,
            "normalized_blocking_issues": norm_blocking,
            "regressions": round_regressions,
            "oracle_fix_applied": False,
            "workspace_hash": ws_hash,
            "workspace_bytes_ESTIMATED": ws_metrics["python_source_bytes_ESTIMATED"],
            "stdout": visible_result["stdout"][:2000],
            "total_output_bytes_ESTIMATED": out_metrics["total_output_bytes_ESTIMATED"],
            "round_duration_seconds_MEASURED": round(round_elapsed, 3),
        }

        round_history.append(round_record)

        if round_verdict == "PASS":
            final_verdict = "PASS"
            final_score = round_score
            final_findings = round_findings
            stop_reason = "VERIFIED_PASS"
            break

        # Semantic stagnation check: if previous round attempted repair, verify progress
        if current_round > 1:
            prev = round_history[-2]
            score_unchanged = (round_score == prev.get("score"))
            blocking_unchanged = (norm_blocking == prev.get("normalized_blocking_issues"))
            hash_unchanged = (ws_hash == prev.get("workspace_hash"))

            if score_unchanged and blocking_unchanged and hash_unchanged:
                stop_reason = "STAGNATION"
                final_verdict = round_verdict
                final_score = round_score
                final_findings = round_findings
                break

        # Try oracle fix — only if FAIL or ABSTAIN and oracle exists
        if round_verdict in ("FAIL", "ABSTAIN", "ERROR"):
            pre_fix_hash = ws_hash
            fix_applied = _apply_oracle_fix(workspace_dir)
            round_record["oracle_fix_applied"] = fix_applied
            post_fix_hash = compute_workspace_hash(workspace_dir)
            round_record["workspace_modified"] = (pre_fix_hash != post_fix_hash)

            if not fix_applied:
                final_verdict = round_verdict
                final_score = round_score
                final_findings = round_findings
                stop_reason = "NO_ORACLE_AVAILABLE"
                break

            if not round_record["workspace_modified"]:
                # The oracle ran but made 0 modifications to files (idempotent repeat)
                stop_reason = "STAGNATION"
                final_verdict = round_verdict
                final_score = round_score
                final_findings = round_findings
                break

            previous_evidence = {"round": current_round, "verdict": round_verdict}

    else:
        # Max rounds reached without early stagnation
        final_verdict = round_history[-1]["verdict"] if round_history else "FAIL"
        final_score = round_history[-1].get("score") if round_history else 0.0
        final_findings = []
        stop_reason = "MAX_ROUNDS_REACHED"

    elapsed = time.time() - t0

    # Context duplication analysis
    duplication = detect_context_duplication(round_history)

    # Total bytes across all rounds
    total_input_bytes = sum(r.get("workspace_bytes_ESTIMATED", 0) for r in round_history)
    total_output_bytes = sum(r.get("total_output_bytes_ESTIMATED", 0) for r in round_history)

    total_subprocess_calls = judge_subprocess_calls + instrumentation_subprocess_calls

    token_summary = build_token_summary(
        condition="the_judge",
        subprocess_calls=total_subprocess_calls,
        workspace_bytes=total_input_bytes,
        total_output_bytes=total_output_bytes,
        duration_seconds=elapsed,
        rounds=len(round_history),
        workspace_hash_ops=workspace_hash_ops,
        judge_subprocess_calls=judge_subprocess_calls,
        instrumentation_subprocess_calls=instrumentation_subprocess_calls,
        duplication=duplication,
    )

    initial_verdict = round_history[0]["verdict"] if round_history else final_verdict
    initial_score = round_history[0].get("score") if round_history else final_score
    oracle_attempted = any(r.get("oracle_fix_applied") for r in round_history)
    oracle_succeeded = oracle_attempted and final_verdict == "PASS"

    return {
        "condition": "the_judge",
        "verdict": final_verdict,
        "initial_verdict": initial_verdict,
        "initial_score": initial_score,
        "stop_reason": stop_reason,
        "oracle_attempted": oracle_attempted,
        "oracle_succeeded": oracle_succeeded,
        "rounds": len(round_history),
        "subprocess_calls_MEASURED": total_subprocess_calls,
        "judge_subprocess_calls_MEASURED": judge_subprocess_calls,
        "instrumentation_subprocess_calls_MEASURED": instrumentation_subprocess_calls,
        "workspace_hash_operations_MEASURED": workspace_hash_ops,
        "regressions": all_regressions,
        "judge_findings": final_findings,
        "judge_score": final_score,
        "visible_tests_passed": last_visible_result["passed_count"] if last_visible_result else 0,
        "visible_tests_failed": last_visible_result["failed_count"] if last_visible_result else 0,
        "round_history": round_history,
        "workspace_metrics": measure_workspace_bytes(workspace_dir),
        "token_summary": token_summary,
        "context_duplication": duplication,
        "duration_seconds_MEASURED": round(elapsed, 3),
        "condition_note": (
            "Controlled benchmark condition: uses the_judge.api.verify() with hard gates and "
            "challenge synthesis. Repair is performed via deterministic oracle apply_fix.py — "
            "NOT a real LLM agent. Measures detection quality and oracle loop dynamics."
        ),
    }
