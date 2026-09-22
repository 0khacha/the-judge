"""
instrumentation.py — Measurement utilities for the A/B/C benchmark.

All metrics are labeled as MEASURED or ESTIMATED in the output.
No LLM token counts exist (The Judge is a deterministic subprocess engine);
we use proxy metrics that are clearly distinguished from real token counts.

Metric labeling convention:
  _MEASURED   — directly observed value (subprocess calls, wall-clock time)
  _ESTIMATED  — proxy/derived value (file bytes → "input token" proxy)
  _UNAVAILABLE — metric cannot be captured in this environment
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# File-content metrics (proxy for "context sent to agent")
# ---------------------------------------------------------------------------

def measure_workspace_bytes(workspace_dir: str) -> Dict[str, Any]:
    """
    Count total bytes of Python source files in the workspace.

    Used as a proxy for "input context" — the amount of code content
    the Judge reads when capturing evidence. Labeled ESTIMATED because
    the Judge does not tokenize; byte count approximates token count
    at roughly 4 bytes/token for English/code text.

    Returns:
        {
            "python_file_count_MEASURED": int,
            "python_source_bytes_ESTIMATED": int,
            "test_file_bytes_ESTIMATED": int,
            "impl_file_bytes_ESTIMATED": int,
        }
    """
    impl_bytes = 0
    test_bytes = 0
    file_count = 0

    for root, _dirs, files in os.walk(workspace_dir):
        # Skip hidden_tests — those are never shown to the conditions
        if "hidden_tests" in root:
            continue
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
            except OSError:
                continue
            file_count += 1
            if "test" in fname.lower() or "test" in root.lower():
                test_bytes += size
            else:
                impl_bytes += size

    return {
        "python_file_count_MEASURED": file_count,
        "python_source_bytes_ESTIMATED": impl_bytes + test_bytes,
        "test_file_bytes_ESTIMATED": test_bytes,
        "impl_file_bytes_ESTIMATED": impl_bytes,
    }


def measure_output_bytes(stdout: str, stderr: str) -> Dict[str, Any]:
    """
    Count bytes in subprocess stdout + stderr.

    Used as a proxy for "output tokens" — the amount of test output
    produced by a verification subprocess call. Labeled ESTIMATED.

    Returns:
        {
            "stdout_bytes_ESTIMATED": int,
            "stderr_bytes_ESTIMATED": int,
            "total_output_bytes_ESTIMATED": int,
        }
    """
    so = len(stdout.encode("utf-8")) if stdout else 0
    se = len(stderr.encode("utf-8")) if stderr else 0
    return {
        "stdout_bytes_ESTIMATED": so,
        "stderr_bytes_ESTIMATED": se,
        "total_output_bytes_ESTIMATED": so + se,
    }


# ---------------------------------------------------------------------------
# Context duplication analysis
# ---------------------------------------------------------------------------

def detect_context_duplication(round_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyse how much content was repeated across correction rounds.

    For each round after the first, compare:
    - Workspace file content and SHA-256 hashes
    - Test output bytes & exact stdout match
    - Blocking issues and finding repetition

    Distinguishes:
    - Repeated file content (re-written or unchanged disk state)
    - Repeated test output / stdout
    - Repeated normalized blocking issues

    Returns:
        {
            "rounds_analyzed_MEASURED": int,
            "repeated_file_content_rounds_MEASURED": int,
            "repeated_stdout_rounds_MEASURED": int,
            "repeated_workspace_hash_rounds_MEASURED": int,
            "repeated_blocking_issue_rounds_MEASURED": int,
            "total_repeated_bytes_ESTIMATED": int,
            "duplication_ratio_ESTIMATED": float,   # 0.0–1.0
            "duplication_note": str,
        }
    """
    if not round_history or len(round_history) < 2:
        return {
            "rounds_analyzed_MEASURED": len(round_history),
            "repeated_file_content_rounds_MEASURED": 0,
            "repeated_stdout_rounds_MEASURED": 0,
            "repeated_workspace_hash_rounds_MEASURED": 0,
            "repeated_blocking_issue_rounds_MEASURED": 0,
            "total_repeated_bytes_ESTIMATED": 0,
            "duplication_ratio_ESTIMATED": 0.0,
            "duplication_note": "Only one round — no repetition possible.",
        }

    repeated_file_rounds = 0
    repeated_stdout_rounds = 0
    repeated_hash_rounds = 0
    repeated_blocking_rounds = 0
    total_repeated_bytes = 0
    total_bytes = 0

    prev_workspace_bytes = round_history[0].get("workspace_bytes_ESTIMATED", 0)
    prev_stdout = round_history[0].get("stdout", "")
    prev_output_bytes = round_history[0].get("total_output_bytes_ESTIMATED", 0)
    prev_hash = round_history[0].get("workspace_hash", "")
    prev_blocking = round_history[0].get("normalized_blocking_issues", [])

    total_bytes += prev_workspace_bytes + prev_output_bytes

    for rnd in round_history[1:]:
        cur_workspace_bytes = rnd.get("workspace_bytes_ESTIMATED", 0)
        cur_stdout = rnd.get("stdout", "")
        cur_output_bytes = rnd.get("total_output_bytes_ESTIMATED", 0)
        cur_hash = rnd.get("workspace_hash", "")
        cur_blocking = rnd.get("normalized_blocking_issues", [])

        total_bytes += cur_workspace_bytes + cur_output_bytes

        if cur_workspace_bytes == prev_workspace_bytes:
            repeated_file_rounds += 1
            total_repeated_bytes += cur_workspace_bytes

        if cur_hash and cur_hash == prev_hash:
            repeated_hash_rounds += 1

        if cur_stdout and cur_stdout == prev_stdout:
            repeated_stdout_rounds += 1
            total_repeated_bytes += cur_output_bytes

        if cur_blocking and cur_blocking == prev_blocking:
            repeated_blocking_rounds += 1

        prev_workspace_bytes = cur_workspace_bytes
        prev_stdout = cur_stdout
        prev_output_bytes = cur_output_bytes
        prev_hash = cur_hash
        prev_blocking = cur_blocking

    ratio = round(total_repeated_bytes / total_bytes, 4) if total_bytes > 0 else 0.0

    note = (
        f"{repeated_file_rounds} round(s) sent unchanged file content; "
        f"{repeated_stdout_rounds} round(s) produced identical test output; "
        f"{repeated_blocking_rounds} round(s) had identical normalized blocking issues."
    )

    return {
        "rounds_analyzed_MEASURED": len(round_history),
        "repeated_file_content_rounds_MEASURED": repeated_file_rounds,
        "repeated_stdout_rounds_MEASURED": repeated_stdout_rounds,
        "repeated_workspace_hash_rounds_MEASURED": repeated_hash_rounds,
        "repeated_blocking_issue_rounds_MEASURED": repeated_blocking_rounds,
        "total_repeated_bytes_ESTIMATED": total_repeated_bytes,
        "duplication_ratio_ESTIMATED": ratio,
        "duplication_note": note,
    }


# ---------------------------------------------------------------------------
# Token-equivalent summary
# ---------------------------------------------------------------------------

def build_token_summary(
    condition: str,
    subprocess_calls: int,
    workspace_bytes: int,
    total_output_bytes: int,
    duration_seconds: float,
    rounds: int,
    workspace_hash_ops: int = 0,
    judge_subprocess_calls: int = 0,
    instrumentation_subprocess_calls: int = 0,
    duplication: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a unified "token-equivalent" summary for a single trial.

    All estimates are clearly labeled. No values are fabricated.
    The Judge does not use an LLM, so traditional token counts are UNAVAILABLE.

    The byte-to-token proxy uses a conservative 4 bytes ≈ 1 token-equivalent for code.
    This is an approximation for comparative purposes only.
    """
    approx_input_token_equiv = workspace_bytes // 4
    approx_output_token_equiv = total_output_bytes // 4

    result: Dict[str, Any] = {
        # --- MEASURED (directly observed) ---
        "condition": condition,
        "subprocess_calls_total_MEASURED": subprocess_calls,
        "judge_verify_subprocess_calls_MEASURED": judge_subprocess_calls or subprocess_calls,
        "instrumentation_subprocess_calls_MEASURED": instrumentation_subprocess_calls,
        "workspace_hash_operations_MEASURED": workspace_hash_ops,
        "verify_api_calls_MEASURED": rounds,          # each round = 1 verify() call
        "correction_rounds_MEASURED": max(0, rounds - 1),
        "duration_seconds_MEASURED": round(duration_seconds, 3),
        # --- ESTIMATED (proxy from byte counts) ---
        "input_bytes_ESTIMATED": workspace_bytes,
        "output_bytes_ESTIMATED": total_output_bytes,
        "approx_input_token_equivalents_ESTIMATED": approx_input_token_equiv,
        "approx_output_token_equivalents_ESTIMATED": approx_output_token_equiv,
        "approx_total_token_equivalents_ESTIMATED": approx_input_token_equiv + approx_output_token_equiv,
        # --- UNAVAILABLE (explicitly null — no LLM) ---
        "llm_input_tokens_UNAVAILABLE": None,
        "llm_output_tokens_UNAVAILABLE": None,
        "llm_cached_tokens_UNAVAILABLE": None,
        "llm_api_calls_UNAVAILABLE": None,
        "token_metric_note": (
            "The Judge is a deterministic subprocess engine — no LLM API calls occur. "
            "All token-equivalent metrics are byte-count proxies (4 bytes ≈ 1 token-equivalent). "
            "They represent disk/subprocess data volume, NOT LLM token usage. "
            "Compare relative ratios between conditions; do not treat as absolute LLM tokens."
        ),
    }

    if duplication:
        result["context_duplication"] = duplication

    return result
