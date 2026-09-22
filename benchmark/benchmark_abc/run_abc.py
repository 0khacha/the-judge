"""
run_abc.py — The Judge A/B/C Benchmark Runner

Independent evaluation of The Judge across three conditions:
  A — Baseline      (no review)
  B — Generic Review (visible tests only)
  C — The Judge     (full verify() + evidence-gated repair loop)

Usage:
    python -m benchmark.benchmark_abc.run_abc
    python -m benchmark.benchmark_abc.run_abc --tasks benchmark/tasks --seed 42
    python -m benchmark.benchmark_abc.run_abc --results benchmark/benchmark_abc/results

Required environment:
    - Python 3.9+
    - pytest installed
    - the-judge package installed or project root in PYTHONPATH
    - Tasks directory with 12 subdirectories (benchmark/tasks/)

Outputs (in results_dir/):
    raw/          — run_<timestamp>.jsonl  (one JSON object per trial line)
    summaries/    — baseline.json, generic_review.json, judge.json
    metrics/      — comparison.json, quality_vs_cost.json, per_task.json,
                    context_duplication.json, advantage_analysis.json
    report/       — benchmark_report.md

Design principles enforced:
    - Fresh isolated temp workspace for every trial
    - Hidden tests never shown to any condition during execution
    - Conditions cannot inherit state from each other
    - All metrics labeled MEASURED / ESTIMATED / UNAVAILABLE
    - No numbers fabricated
    - All results saved regardless of outcome (unfavorable results kept)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path (needed when running as module from project root)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from benchmark.benchmark_abc.analysis import (
    analyze_judge_advantage_cases,
    compute_condition_summary,
    compute_duplication_stats,
    compute_per_task_comparison,
    compute_quality_vs_cost,
)
from benchmark.benchmark_abc.conditions import (
    run_condition_a_baseline,
    run_condition_b_generic_review,
    run_condition_c_the_judge,
)
from benchmark.benchmark_abc.independent_evaluator import classify_outcome, run_hidden_evaluator
from benchmark.benchmark_abc.report_generator import generate_report
from benchmark.benchmark_abc.task_catalog import TASK_CATALOG, TASK_BY_ID

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONDITIONS = ["baseline", "generic_review", "the_judge"]
CONDITION_RUNNERS = {
    "baseline": run_condition_a_baseline,
    "generic_review": run_condition_b_generic_review,
    "the_judge": run_condition_c_the_judge,
}


# ---------------------------------------------------------------------------
# Per-trial execution
# ---------------------------------------------------------------------------

def run_single_trial(
    task_id: str,
    condition: str,
    tasks_dir: str,
    run_id: str,
    seed: int,
) -> Dict[str, Any]:
    """
    Execute one trial: isolate workspace → run condition → evaluate hidden tests.

    Returns a complete trial record for storage.

    Isolation guarantee:
        Each trial gets its own tempfile.mkdtemp() workspace.
        The source task directory is NEVER modified.
        Conditions cannot share workspaces.
    """
    src_task_path = os.path.abspath(os.path.join(tasks_dir, task_id))

    if not os.path.isdir(src_task_path):
        return {
            "run_id": run_id,
            "task": task_id,
            "condition": condition,
            "error": f"Task directory not found: {src_task_path}",
        }

    # Create isolated workspace
    temp_base = tempfile.mkdtemp(prefix=f"abc_bench_{task_id}_{condition}_")
    workspace_dir = os.path.join(temp_base, task_id)

    try:
        shutil.copytree(src_task_path, workspace_dir)
    except Exception as exc:
        shutil.rmtree(temp_base, ignore_errors=True)
        return {
            "run_id": run_id,
            "task": task_id,
            "condition": condition,
            "error": f"Failed to copy task: {exc}",
        }

    try:
        t0 = time.time()

        # Run the condition
        runner = CONDITION_RUNNERS[condition]
        task_info = TASK_BY_ID.get(task_id, {"task_id": task_id})
        condition_result = runner(workspace_dir, task_info)

        # Run independent hidden evaluator AFTER condition completes
        # (hidden tests are present in the workspace copy but not used by conditions)
        ground_truth = run_hidden_evaluator(workspace_dir)

        elapsed = time.time() - t0

        # Classify outcome against ground truth
        condition_verdict = condition_result.get("verdict", "UNKNOWN")
        gt_verdict = ground_truth.get("ground_truth_verdict", "ERROR")
        outcome = classify_outcome(condition_verdict, gt_verdict)

        # Build compact per-trial record
        token_summary = condition_result.get("token_summary", {})

        record: Dict[str, Any] = {
            "run_id": run_id,
            "task": task_id,
            "task_difficulty": task_info.get("difficulty", "?"),
            "task_defect_type": task_info.get("defect_type", "?"),
            "condition": condition,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seed": seed,
            # Verdict + ground truth
            "condition_verdict": condition_verdict,
            "initial_verdict": condition_result.get("initial_verdict", condition_verdict),
            "ground_truth_verdict": gt_verdict,
            # Outcome classification
            "outcome": outcome,
            "success": outcome.get("success", False),
            "false_pass": outcome.get("is_false_pass", False),
            "true_pass": outcome.get("is_true_pass", False),
            "false_fail": outcome.get("is_false_fail", False),
            "true_fail": outcome.get("is_true_fail", False),
            "human_review_required": condition_verdict in ("ABSTAIN", "HUMAN_REVIEW_REQUIRED"),
            "oracle_attempted": condition_result.get("oracle_attempted", False),
            "oracle_succeeded": condition_result.get("oracle_succeeded", False),
            # Cost metrics (MEASURED)
            "rounds_MEASURED": condition_result.get("rounds", 1),
            "subprocess_calls_MEASURED": condition_result.get("subprocess_calls_MEASURED", 0),
            "judge_subprocess_calls_MEASURED": condition_result.get("judge_subprocess_calls_MEASURED", 0),
            "instrumentation_subprocess_calls_MEASURED": condition_result.get("instrumentation_subprocess_calls_MEASURED", 0),
            "workspace_hash_operations_MEASURED": condition_result.get("workspace_hash_operations_MEASURED", 0),
            "duration_seconds_MEASURED": condition_result.get("duration_seconds_MEASURED", elapsed),
            # Cost metrics (ESTIMATED)
            "input_bytes_ESTIMATED": token_summary.get("input_bytes_ESTIMATED", 0),
            "output_bytes_ESTIMATED": token_summary.get("output_bytes_ESTIMATED", 0),
            "approx_input_token_equivalents_ESTIMATED": token_summary.get("approx_input_token_equivalents_ESTIMATED", 0),
            "approx_output_token_equivalents_ESTIMATED": token_summary.get("approx_output_token_equivalents_ESTIMATED", 0),
            "approx_total_token_equivalents_ESTIMATED": token_summary.get("approx_total_token_equivalents_ESTIMATED", 0),
            # Backwards-compat aliases
            "approx_input_tokens_ESTIMATED": token_summary.get("approx_input_token_equivalents_ESTIMATED", 0),
            "approx_output_tokens_ESTIMATED": token_summary.get("approx_output_token_equivalents_ESTIMATED", 0),
            "approx_total_tokens_ESTIMATED": token_summary.get("approx_total_token_equivalents_ESTIMATED", 0),
            # Cost metrics (UNAVAILABLE — explicit null)
            "llm_input_tokens_UNAVAILABLE": None,
            "llm_output_tokens_UNAVAILABLE": None,
            "llm_cached_tokens_UNAVAILABLE": None,
            "llm_api_calls_UNAVAILABLE": None,
            # Test results
            "visible_tests_passed": condition_result.get("visible_tests_passed"),
            "visible_tests_failed": condition_result.get("visible_tests_failed"),
            "hidden_tests_passed": ground_truth.get("hidden_tests_passed", 0),
            "hidden_tests_failed": ground_truth.get("hidden_tests_failed", 0),
            "hidden_tests_total": ground_truth.get("hidden_tests_total", 0),
            # Judge-specific
            "judge_score": condition_result.get("judge_score"),
            "judge_findings_count": len(condition_result.get("judge_findings", [])),
            "regressions_detected": len(condition_result.get("regressions", [])),
            # Context duplication (Judge only)
            "context_duplication": condition_result.get("context_duplication"),
            # Full detail (stored for audit trail)
            "condition_result": condition_result,
            "ground_truth": ground_truth,
        }

        return record

    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


# ---------------------------------------------------------------------------
# Main benchmark runner
# ---------------------------------------------------------------------------

def run_abc_benchmark(
    tasks_dir: str = "benchmark/tasks",
    results_dir: str = "benchmark/benchmark_abc/results",
    seed: int = 42,
    runs: int = 1,
    max_judge_rounds: int = 5,
) -> Dict[str, Any]:
    """
    Execute the full A/B/C benchmark across all tasks and conditions.

    Args:
        tasks_dir: Directory containing task subdirectories
        results_dir: Directory where results will be written
        seed: Random seed for trial ordering
        runs: Number of independent runs per task/condition (default: 1)
        max_judge_rounds: Maximum repair rounds for Condition C (default: 5)

    Returns:
        Summary dict with all computed metrics
    """
    random.seed(seed)

    tasks_dir_abs = os.path.abspath(tasks_dir)
    results_dir_abs = os.path.abspath(results_dir)

    # Create output directories
    for subdir in ["raw", "summaries", "metrics", "report"]:
        os.makedirs(os.path.join(results_dir_abs, subdir), exist_ok=True)

    if not os.path.isdir(tasks_dir_abs):
        print(f"[ERROR] Tasks directory not found: {tasks_dir_abs}", file=sys.stderr)
        return {}

    # Discover tasks
    task_ids = sorted([
        d for d in os.listdir(tasks_dir_abs)
        if os.path.isdir(os.path.join(tasks_dir_abs, d))
    ])

    if not task_ids:
        print(f"[ERROR] No task directories found in: {tasks_dir_abs}", file=sys.stderr)
        return {}

    print(f"\n{'='*70}")
    print(f"  THE JUDGE A/B/C BENCHMARK -- Independent Rigorous Evaluation")
    print(f"{'='*70}")
    print(f"\nTasks directory : {tasks_dir_abs}")
    print(f"Results         : {results_dir_abs}")
    print(f"Tasks found     : {len(task_ids)}")
    print(f"Conditions      : {', '.join(CONDITIONS)}")
    print(f"Runs per trial  : {runs}")
    print(f"Random seed     : {seed}")
    print(f"\nNote: Token metrics are byte-count proxies (ESTIMATED).")
    print(f"      The Judge uses no LLM. See report for full disclosure.\n")

    # Build trial list: (task_id, condition)
    trials: List[Tuple[str, str]] = []
    for _ in range(runs):
        for task_id in task_ids:
            for cond in CONDITIONS:
                trials.append((task_id, cond))

    random.shuffle(trials)
    print(f"Total trials    : {len(trials)} (shuffled, seed={seed})\n")

    # ------------------------------------------------------------------ #
    # Execute trials
    # ------------------------------------------------------------------ #
    all_results: List[Dict[str, Any]] = []
    results_by_condition: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CONDITIONS}

    ts_start = time.strftime("%Y%m%dT%H%M%S")
    raw_file = os.path.join(results_dir_abs, "raw", f"run_{ts_start}.jsonl")

    with open(raw_file, "w", encoding="utf-8") as raw_fh:
        for idx, (task_id, cond) in enumerate(trials, 1):
            run_id = f"abc_{ts_start}_{idx:04d}"
            label = f"Trial {idx:03d}/{len(trials):03d} | {task_id:30s} | {cond}"
            print(label, end="", flush=True)

            record = run_single_trial(
                task_id=task_id,
                condition=cond,
                tasks_dir=tasks_dir_abs,
                run_id=run_id,
                seed=seed,
            )

            verdict = record.get("condition_verdict", "ERROR")
            gt = record.get("ground_truth_verdict", "ERROR")
            cls = record.get("outcome", {}).get("classification", "?")
            dur = record.get("duration_seconds_MEASURED", 0.0)

            print(f" -> {verdict:7s} | GT:{gt:4s} | {cls:12s} | {dur:.2f}s")

            all_results.append(record)
            results_by_condition[cond].append(record)

            # Write raw record immediately (one JSON per line)
            raw_fh.write(json.dumps(record, default=str) + "\n")
            raw_fh.flush()

    print(f"\n[Benchmark] All {len(trials)} trials complete.\n")

    # ------------------------------------------------------------------ #
    # Compute summaries
    # ------------------------------------------------------------------ #
    print("[Analysis] Computing condition summaries...")
    b_summary = compute_condition_summary(results_by_condition["baseline"], "baseline")
    g_summary = compute_condition_summary(results_by_condition["generic_review"], "generic_review")
    j_summary = compute_condition_summary(results_by_condition["the_judge"], "the_judge")

    summaries = {
        "baseline": b_summary,
        "generic_review": g_summary,
        "the_judge": j_summary,
    }

    # ------------------------------------------------------------------ #
    # Per-task comparison
    # ------------------------------------------------------------------ #
    print("[Analysis] Computing per-task comparison matrix...")
    per_task = compute_per_task_comparison(
        results_by_condition["baseline"],
        results_by_condition["generic_review"],
        results_by_condition["the_judge"],
        task_catalog=TASK_BY_ID,
    )

    # ------------------------------------------------------------------ #
    # Quality-vs-cost
    # ------------------------------------------------------------------ #
    print("[Analysis] Computing quality-vs-cost metrics...")
    quality_vs_cost = compute_quality_vs_cost(b_summary, g_summary, j_summary)

    # ------------------------------------------------------------------ #
    # Context duplication
    # ------------------------------------------------------------------ #
    print("[Analysis] Computing context duplication statistics...")
    duplication_stats = compute_duplication_stats(results_by_condition["the_judge"])

    # ------------------------------------------------------------------ #
    # Advantage analysis
    # ------------------------------------------------------------------ #
    print("[Analysis] Analyzing Judge advantage/regression cases...")
    advantage_analysis = analyze_judge_advantage_cases(per_task)

    # ------------------------------------------------------------------ #
    # Write summaries
    # ------------------------------------------------------------------ #
    print("[Output] Writing summaries...")
    for cond_name, summary in summaries.items():
        fp = os.path.join(results_dir_abs, "summaries", f"{cond_name}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)

    # ------------------------------------------------------------------ #
    # Write metrics
    # ------------------------------------------------------------------ #
    print("[Output] Writing metrics...")
    metrics_dir = os.path.join(results_dir_abs, "metrics")

    comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seed": seed,
        "tasks_count": len(task_ids),
        "runs_per_trial": runs,
        "summaries": summaries,
    }
    with open(os.path.join(metrics_dir, "comparison.json"), "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, default=str)

    with open(os.path.join(metrics_dir, "quality_vs_cost.json"), "w", encoding="utf-8") as f:
        json.dump(quality_vs_cost, f, indent=2, default=str)

    with open(os.path.join(metrics_dir, "per_task.json"), "w", encoding="utf-8") as f:
        json.dump(per_task, f, indent=2, default=str)

    with open(os.path.join(metrics_dir, "context_duplication.json"), "w", encoding="utf-8") as f:
        json.dump(duplication_stats, f, indent=2, default=str)

    with open(os.path.join(metrics_dir, "advantage_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(advantage_analysis, f, indent=2, default=str)

    # ------------------------------------------------------------------ #
    # Generate report
    # ------------------------------------------------------------------ #
    print("[Output] Generating benchmark report...")
    run_metadata = {
        "task_count": len(task_ids),
        "seed": seed,
        "runs_per_trial": runs,
        "model": "N/A — The Judge is a deterministic subprocess engine (no LLM)",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    report_md = generate_report(
        summaries=summaries,
        per_task=per_task,
        quality_vs_cost=quality_vs_cost,
        duplication_stats=duplication_stats,
        advantage_analysis=advantage_analysis,
        run_metadata=run_metadata,
    )

    report_path = os.path.join(results_dir_abs, "report", "benchmark_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    deterministic_report_path = os.path.abspath(os.path.join(_PROJECT_ROOT, "benchmark", "THE_JUDGE_DETERMINISTIC_REPORT.md"))
    with open(deterministic_report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # ------------------------------------------------------------------ #
    # Print scorecard
    # ------------------------------------------------------------------ #
    print(f"\n{'='*80}")
    print(f"  A/B/C BENCHMARK SCORECARD  (n={len(task_ids)} tasks × {runs} run(s))")
    print(f"{'='*80}")
    print(
        f"{'Metric':<40} {'Baseline':>10} {'Generic Rev':>12} {'The Judge':>12}"
    )
    print("-" * 80)

    def _pct_f(v):
        return f"{v * 100:.1f}%"

    rows_sc = [
        ("Initial defect detection rate", "initial_detection_rejection_rate"),
        ("False PASS rate (FP / PASS claims)", "false_pass_rate"),
        ("Unconditional False PASS (FP / total)", "unconditional_false_pass_rate"),
        ("Verified correct delivery (TP / total)", "verified_correct_delivery_rate"),
        ("Final correct code rate ((TP+FN)/total)", "final_correct_implementation_rate"),
        ("Balanced accuracy", "balanced_accuracy"),
        ("Reliability ((TP+TN)/total)", "reliability"),
    ]
    for label, key in rows_sc:
        bv = b_summary.get(key, 0.0)
        gv = g_summary.get(key, 0.0)
        jv = j_summary.get(key, 0.0)
        print(f"{label:<42} {_pct_f(bv):>10} {_pct_f(gv):>12} {_pct_f(jv):>12}")

    print("-" * 80)
    print(
        f"{'Mean subprocess calls total (MEASURED)':<42} "
        f"{b_summary.get('mean_subprocess_calls_total_MEASURED', 0):>10.1f} "
        f"{g_summary.get('mean_subprocess_calls_total_MEASURED', 0):>12.1f} "
        f"{j_summary.get('mean_subprocess_calls_total_MEASURED', 0):>12.1f}"
    )
    print(
        f"{'— Judge sandbox calls only (MEASURED)':<42} "
        f"{b_summary.get('mean_judge_subprocess_calls_MEASURED', 0):>10.1f} "
        f"{g_summary.get('mean_judge_subprocess_calls_MEASURED', 0):>12.1f} "
        f"{j_summary.get('mean_judge_subprocess_calls_MEASURED', 0):>12.1f}"
    )
    print(
        f"{'Mean duration seconds (MEASURED)':<42} "
        f"{b_summary.get('mean_duration_seconds_MEASURED', 0):>10.3f} "
        f"{g_summary.get('mean_duration_seconds_MEASURED', 0):>12.3f} "
        f"{j_summary.get('mean_duration_seconds_MEASURED', 0):>12.3f}"
    )
    print(
        f"{'Mean total token-equiv (ESTIMATED)':<42} "
        f"{b_summary.get('mean_total_token_equivalents_ESTIMATED', 0):>10} "
        f"{g_summary.get('mean_total_token_equivalents_ESTIMATED', 0):>12} "
        f"{j_summary.get('mean_total_token_equivalents_ESTIMATED', 0):>12}"
    )
    print("=" * 80)

    qc = quality_vs_cost
    qcomp = qc.get("quality_comparison", {})
    to = qc.get("token_equivalent_overhead_ESTIMATED", {})
    ro = qc.get("runtime_overhead_MEASURED", {})

    print(f"\nKey findings:")
    print(f"  Initial defect detection (Judge vs Baseline): {_pct_f(qcomp.get('detection_rate', {}).get('the_judge', 0.0))}")
    print(f"  False PASS reduction (Judge vs Baseline):     {_pct_f(qcomp.get('false_pass_reduction_vs_baseline', 0.0))}")
    print(f"  Verified delivery delta (Judge vs Baseline):   {_pct_f(qcomp.get('verified_delivery_delta_vs_baseline', 0.0))}")
    print(f"  Token-equiv overhead (Judge vs Baseline):     {to.get('judge_vs_baseline_ratio', 'N/A')}x (ESTIMATED byte proxy)")
    print(f"  Runtime overhead (Judge vs Baseline):         {ro.get('judge_vs_baseline_seconds', 0):.3f}s (MEASURED)")
    print(f"  Judge advantage tasks (IMPROVEMENT):          {advantage_analysis.get('judge_improves_quality', {}).get('count', 0)}")
    print(f"  Judge regression tasks (REGRESSION):          {advantage_analysis.get('judge_hurts_performance', {}).get('count', 0)}")
    print(f"  Judge unverified detection tasks:             {advantage_analysis.get('judge_detected_but_unverified', {}).get('count', 0)}")
    print(f"\nOutputs:")
    print(f"  Raw records  : {raw_file}")
    print(f"  Report       : {report_path}")
    print(f"  Metrics      : {metrics_dir}/")
    print(f"  Summaries    : {os.path.join(results_dir_abs, 'summaries')}/")
    print()

    return {
        "summaries": summaries,
        "per_task": per_task,
        "quality_vs_cost": quality_vs_cost,
        "advantage_analysis": advantage_analysis,
        "duplication_stats": duplication_stats,
        "raw_file": raw_file,
        "report_path": report_path,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="The Judge A/B/C Benchmark — Independent rigorous evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--tasks",
        default="benchmark/tasks",
        help="Path to tasks directory (default: benchmark/tasks)",
    )
    parser.add_argument(
        "--results",
        default="benchmark/benchmark_abc/results",
        help="Path to results directory (default: benchmark/benchmark_abc/results)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for trial ordering (default: 42)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of independent runs per task/condition (default: 1)",
    )
    parser.add_argument(
        "--max-judge-rounds",
        type=int,
        default=5,
        help="Maximum repair rounds for Condition C (default: 5)",
    )

    args = parser.parse_args()

    run_abc_benchmark(
        tasks_dir=args.tasks,
        results_dir=args.results,
        seed=args.seed,
        runs=args.runs,
        max_judge_rounds=args.max_judge_rounds,
    )


if __name__ == "__main__":
    main()
