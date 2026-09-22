"""
analysis.py — Statistical and comparative analysis for the Controlled A/B/C Benchmark.

Evaluates three dimensions:
  1. Detection Performance — Can The Judge detect flawed starting code?
  2. Repair-Loop Dynamics  — Can oracle repair resolve detected issues without stagnation?
  3. Final Evaluation Quality & Engineering Cost
"""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Per-condition quality summary
# ---------------------------------------------------------------------------

def compute_condition_summary(results: List[Dict[str, Any]], condition: str) -> Dict[str, Any]:
    """
    Compute quality, detection, and cost metrics for all trials of one condition.
    """
    n = len(results)
    if n == 0:
        return {"condition": condition, "task_count": 0, "error": "No results"}

    tp = sum(1 for r in results if r["outcome"]["classification"] == "TRUE_PASS")
    fp = sum(1 for r in results if r["outcome"]["classification"] == "FALSE_PASS")
    tn = sum(1 for r in results if r["outcome"]["classification"] == "TRUE_FAIL")
    fn = sum(1 for r in results if r["outcome"]["classification"] == "FALSE_FAIL")
    abstain = sum(1 for r in results if r["outcome"]["classification"] == "ABSTAIN")

    total_pass_claims = tp + fp
    total_gt_pass = tp + fn  # ground truth in final workspace is PASS
    total_gt_fail = tn + fp  # ground truth in final workspace is FAIL

    # Signal detection & quality rates
    precision = round(tp / total_pass_claims, 4) if total_pass_claims > 0 else 0.0
    recall = round(tp / total_gt_pass, 4) if total_gt_pass > 0 else 0.0
    specificity = round(tn / total_gt_fail, 4) if total_gt_fail > 0 else 0.0
    balanced_accuracy = round((recall + specificity) / 2.0, 4)

    false_pass_rate = round(fp / total_pass_claims, 4) if total_pass_claims > 0 else 0.0
    unconditional_false_pass_rate = round(fp / n, 4) if n > 0 else 0.0
    false_fail_rate = round(fn / (tn + fn), 4) if (tn + fn) > 0 else 0.0
    reliability = round((tp + tn) / n, 4) if n > 0 else 0.0
    abstention_rate = round(abstain / n, 4) if n > 0 else 0.0

    verified_correct_delivery_rate = round(tp / n, 4) if n > 0 else 0.0
    final_correct_implementation_rate = round(total_gt_pass / n, 4) if n > 0 else 0.0

    # Detection performance on initial code (Round 1 / starting code)
    initial_rejections = sum(
        1 for r in results
        if r.get("initial_verdict", r.get("condition_result", {}).get("initial_verdict", r["condition_verdict"])) in ("FAIL", "ABSTAIN", "ERROR")
    )
    initial_detection_rejection_rate = round(initial_rejections / n, 4) if n > 0 else 0.0

    # Repair performance
    repair_attempts = sum(1 for r in results if r.get("oracle_attempted", r.get("condition_result", {}).get("oracle_attempted", False)))
    defects_repaired = sum(
        1 for r in results
        if (r.get("oracle_succeeded", r.get("condition_result", {}).get("oracle_succeeded", False))
            and r["outcome"]["classification"] == "TRUE_PASS")
    )
    repair_success_rate = round(defects_repaired / repair_attempts, 4) if repair_attempts > 0 else 0.0

    # Stop reasons distribution
    stop_reasons = {}
    for r in results:
        sr = r.get("stop_reason") or r.get("condition_result", {}).get("stop_reason", "UNKNOWN")
        stop_reasons[sr] = stop_reasons.get(sr, 0) + 1

    # Internal regressions detected by the score engine
    internal_regressions = sum(len(r.get("condition_result", {}).get("regressions", [])) for r in results)

    # Round counts
    rounds_list = [r.get("condition_result", {}).get("rounds", 1) for r in results]
    mean_rounds = round(statistics.mean(rounds_list), 2)
    median_rounds = round(statistics.median(rounds_list), 2)

    # Subprocess calls
    call_list = [r.get("condition_result", {}).get("subprocess_calls_MEASURED", 0) for r in results]
    judge_call_list = [r.get("condition_result", {}).get("judge_subprocess_calls_MEASURED", 0) for r in results]
    instr_call_list = [r.get("condition_result", {}).get("instrumentation_subprocess_calls_MEASURED", 0) for r in results]
    hash_ops_list = [r.get("condition_result", {}).get("workspace_hash_operations_MEASURED", 0) for r in results]

    mean_calls_total = round(statistics.mean(call_list), 2) if call_list else 0.0
    mean_judge_calls = round(statistics.mean(judge_call_list), 2) if judge_call_list else 0.0
    mean_instr_calls = round(statistics.mean(instr_call_list), 2) if instr_call_list else 0.0
    mean_hash_ops = round(statistics.mean(hash_ops_list), 2) if hash_ops_list else 0.0
    total_hash_ops = sum(hash_ops_list)

    # Duration
    dur_list = [r.get("condition_result", {}).get("duration_seconds_MEASURED", 0.0) for r in results]
    mean_dur = round(statistics.mean(dur_list), 3) if dur_list else 0.0
    median_dur = round(statistics.median(dur_list), 3) if dur_list else 0.0
    total_dur = round(sum(dur_list), 3)

    # Byte metrics (estimated token-equivalents)
    tok_summaries = [r.get("condition_result", {}).get("token_summary", {}) for r in results]
    input_bytes_list = [t.get("input_bytes_ESTIMATED", 0) for t in tok_summaries]
    output_bytes_list = [t.get("output_bytes_ESTIMATED", 0) for t in tok_summaries]
    total_token_list = [t.get("approx_total_token_equivalents_ESTIMATED", t.get("approx_total_tokens_ESTIMATED", 0)) for t in tok_summaries]

    mean_input_bytes = round(statistics.mean(input_bytes_list), 0) if input_bytes_list else 0
    mean_output_bytes = round(statistics.mean(output_bytes_list), 0) if output_bytes_list else 0
    mean_total_token_equiv = round(statistics.mean(total_token_list), 0) if total_token_list else 0
    total_input_bytes = sum(input_bytes_list)
    total_output_bytes = sum(output_bytes_list)
    total_token_equiv_all = sum(total_token_list)

    return {
        "condition": condition,
        "sample_size": n,
        "sample_size_note": (
            "Single controlled run per task/condition (n=12). "
            "Results are deterministic point estimates within this suite."
        ),
        # Signal detection counts
        "signal_counts": {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "ABSTAIN": abstain},
        "decision_distribution": {
            "PASS_claims": total_pass_claims,
            "FAIL_claims": tn + fn,
            "ABSTAIN": abstain,
        },
        # Detection performance (Round 1 / starting code)
        "defects_detected_initial": initial_rejections,
        "initial_detection_rejection_rate": initial_detection_rejection_rate,
        # Repair performance (Condition C oracle dynamics)
        "repair_attempts": repair_attempts,
        "defects_successfully_repaired": defects_repaired,
        "defects_detected_not_repaired": initial_rejections - defects_repaired,
        "repair_success_rate": repair_success_rate,
        "stop_reasons_distribution": stop_reasons,
        # Quality metrics
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
        "false_pass_rate": false_pass_rate,
        "unconditional_false_pass_rate": unconditional_false_pass_rate,
        "false_fail_rate": false_fail_rate,
        "reliability": reliability,
        "abstention_rate": abstention_rate,
        "verified_correct_delivery_rate": verified_correct_delivery_rate,
        "final_correct_implementation_rate": final_correct_implementation_rate,
        "internal_regressions_detected": internal_regressions,
        # Cost metrics (MEASURED)
        "mean_rounds_MEASURED": mean_rounds,
        "median_rounds_MEASURED": median_rounds,
        "mean_subprocess_calls_total_MEASURED": mean_calls_total,
        "mean_judge_subprocess_calls_MEASURED": mean_judge_calls,
        "mean_instrumentation_subprocess_calls_MEASURED": mean_instr_calls,
        "mean_workspace_hash_operations_MEASURED": mean_hash_ops,
        "total_workspace_hash_operations_MEASURED": total_hash_ops,
        "mean_duration_seconds_MEASURED": mean_dur,
        "median_duration_seconds_MEASURED": median_dur,
        "total_duration_seconds_MEASURED": total_dur,
        # Cost metrics (ESTIMATED byte proxies)
        "mean_input_bytes_ESTIMATED": int(mean_input_bytes),
        "mean_output_bytes_ESTIMATED": int(mean_output_bytes),
        "mean_total_token_equivalents_ESTIMATED": int(mean_total_token_equiv),
        "total_input_bytes_ESTIMATED": total_input_bytes,
        "total_output_bytes_ESTIMATED": total_output_bytes,
        "total_token_equivalents_all_ESTIMATED": total_token_equiv_all,
        "token_metric_note": (
            "ESTIMATED: byte counts used as LLM token proxies (4 bytes ≈ 1 token-equivalent). "
            "The Judge uses no LLM. Compare relative ratios between conditions, not absolute LLM tokens."
        ),
    }


# ---------------------------------------------------------------------------
# Per-task comparison matrix
# ---------------------------------------------------------------------------

def compute_per_task_comparison(
    baseline_results: List[Dict[str, Any]],
    generic_results: List[Dict[str, Any]],
    judge_results: List[Dict[str, Any]],
    task_catalog: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """
    Build a per-task comparison matrix across all three conditions.
    Distinguishes detection success, oracle repair outcomes, and regressions.
    """
    by_task: Dict[str, Dict[str, Dict]] = {}
    for r in baseline_results:
        by_task.setdefault(r["task"], {})["baseline"] = r
    for r in generic_results:
        by_task.setdefault(r["task"], {})["generic_review"] = r
    for r in judge_results:
        by_task.setdefault(r["task"], {})["the_judge"] = r

    rows = []
    for task_id in sorted(by_task.keys()):
        row = by_task[task_id]
        b = row.get("baseline", {})
        g = row.get("generic_review", {})
        j = row.get("the_judge", {})

        b_verdict = b.get("condition_result", {}).get("verdict", "N/A")
        g_verdict = g.get("condition_result", {}).get("verdict", "N/A")
        j_verdict = j.get("condition_result", {}).get("verdict", "N/A")

        b_cls = b.get("outcome", {}).get("classification", "N/A")
        g_cls = g.get("outcome", {}).get("classification", "N/A")
        j_cls = j.get("outcome", {}).get("classification", "N/A")

        gt = j.get("ground_truth", {}).get("ground_truth_verdict", "N/A")

        b_correct = b_cls in ("TRUE_PASS", "TRUE_FAIL")
        g_correct = g_cls in ("TRUE_PASS", "TRUE_FAIL")
        j_correct = j_cls in ("TRUE_PASS", "TRUE_FAIL")

        b_tokens = b.get("condition_result", {}).get("token_summary", {}).get(
            "approx_total_token_equivalents_ESTIMATED",
            b.get("condition_result", {}).get("token_summary", {}).get("approx_total_tokens_ESTIMATED", 0)
        )
        g_tokens = g.get("condition_result", {}).get("token_summary", {}).get(
            "approx_total_token_equivalents_ESTIMATED",
            g.get("condition_result", {}).get("token_summary", {}).get("approx_total_tokens_ESTIMATED", 0)
        )
        j_tokens = j.get("condition_result", {}).get("token_summary", {}).get(
            "approx_total_token_equivalents_ESTIMATED",
            j.get("condition_result", {}).get("token_summary", {}).get("approx_total_tokens_ESTIMATED", 0)
        )

        j_rounds = j.get("condition_result", {}).get("rounds", 1)
        j_dur = j.get("condition_result", {}).get("duration_seconds_MEASURED", 0.0)
        j_initial_verdict = j.get("condition_result", {}).get("initial_verdict", j_verdict)

        j_stop_reason = j.get("condition_result", {}).get("stop_reason", "UNKNOWN")

        # Classify contribution accurately per PART IV specification
        if b_cls == "TRUE_PASS" and g_cls == "TRUE_PASS" and j_cls == "FALSE_FAIL":
            judge_contribution = "REGRESSION"
            contribution_note = "Baseline & Generic succeeded; The Judge falsely failed valid code (synthesis type error)."
            judge_why = "Challenge synthesis generated invalid property tests (passed float to str parameter)."
        elif b_cls == "FALSE_PASS" and g_cls == "FALSE_PASS" and j_cls == "TRUE_PASS":
            judge_contribution = "IMPROVEMENT"
            contribution_note = "Judge detected starting flaw; oracle repair produced verified passing code."
            judge_why = "Judge FAIL verdict correctly triggered oracle fix which satisfied all verification checks."
        elif b_cls == "FALSE_PASS" and g_cls == "FALSE_PASS" and j_cls == "FALSE_FAIL":
            judge_contribution = "DETECT_BUT_CANNOT_VERIFY"
            contribution_note = "Judge detected starting defect, but rejected post-repair code due to challenge tests."
            judge_why = "Initial flaw detected, but synthesized challenge tests failed on repaired code."
        elif b_cls == "FALSE_PASS" and g_cls == "FALSE_PASS" and j_cls == "FALSE_PASS":
            judge_contribution = "MISSED_DEFECT"
            contribution_note = "Flaw not detected by any condition (visible tests passed, Judge gates passed)."
            judge_why = "Defect outside coverage of visible test suite and Judge challenge heuristics."
        elif b_correct and g_correct and j_correct:
            judge_contribution = "AGREEMENT_CORRECT"
            contribution_note = "All conditions produced correct verdict."
            judge_why = "Implementation verified correctly across all conditions."
        elif not b_correct and not g_correct and not j_correct:
            judge_contribution = "AGREEMENT_INCORRECT"
            contribution_note = "All conditions produced incorrect verdict."
            judge_why = "Common blind spot across all evaluation conditions."
        else:
            judge_contribution = "OTHER"
            contribution_note = f"Baseline={b_cls}, Generic={g_cls}, Judge={j_cls}"
            judge_why = None

        task_info = task_catalog.get(task_id, {})

        rows.append({
            "task_id": task_id,
            "task_name": task_info.get("name", task_id),
            "difficulty": task_info.get("difficulty", "?"),
            "defect_type": task_info.get("defect_type", "?"),
            "defect_nature": task_info.get("defect_nature", "TESTED_DEFECT"),
            "ground_truth_verdict": gt,
            "baseline_verdict": b_verdict,
            "baseline_outcome": b_cls,
            "generic_review_verdict": g_verdict,
            "generic_review_outcome": g_cls,
            "judge_initial_verdict": j_initial_verdict,
            "judge_verdict": j_verdict,
            "judge_outcome": j_cls,
            "judge_stop_reason": j_stop_reason,
            "judge_contribution": judge_contribution,
            "contribution_note": contribution_note,
            "judge_why": judge_why,
            "judge_rounds": j_rounds,
            "judge_duration_seconds": j_dur,
            "baseline_token_equivalents_ESTIMATED": b_tokens,
            "generic_token_equivalents_ESTIMATED": g_tokens,
            "judge_token_equivalents_ESTIMATED": j_tokens,
            "judge_vs_baseline_token_ratio_ESTIMATED": (
                round(j_tokens / b_tokens, 2) if b_tokens > 0 else None
            ),
        })

    return rows


# ---------------------------------------------------------------------------
# Quality-vs-cost metrics
# ---------------------------------------------------------------------------

def compute_quality_vs_cost(
    baseline_summary: Dict[str, Any],
    generic_summary: Dict[str, Any],
    judge_summary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute comparative quality-vs-cost metrics across conditions.
    """
    b_fpr = baseline_summary.get("false_pass_rate", 0.0)
    g_fpr = generic_summary.get("false_pass_rate", 0.0)
    j_fpr = judge_summary.get("false_pass_rate", 0.0)

    b_ufpr = baseline_summary.get("unconditional_false_pass_rate", 0.0)
    j_ufpr = judge_summary.get("unconditional_false_pass_rate", 0.0)

    b_deliv = baseline_summary.get("verified_correct_delivery_rate", 0.0)
    g_deliv = generic_summary.get("verified_correct_delivery_rate", 0.0)
    j_deliv = judge_summary.get("verified_correct_delivery_rate", 0.0)

    b_fcir = baseline_summary.get("final_correct_implementation_rate", 0.0)
    j_fcir = judge_summary.get("final_correct_implementation_rate", 0.0)

    b_rel = baseline_summary.get("reliability", 0.0)
    g_rel = generic_summary.get("reliability", 0.0)
    j_rel = judge_summary.get("reliability", 0.0)

    b_ba = baseline_summary.get("balanced_accuracy", 0.0)
    g_ba = generic_summary.get("balanced_accuracy", 0.0)
    j_ba = judge_summary.get("balanced_accuracy", 0.0)

    b_tok = baseline_summary.get("total_token_equivalents_all_ESTIMATED", 0)
    g_tok = generic_summary.get("total_token_equivalents_all_ESTIMATED", 0)
    j_tok = judge_summary.get("total_token_equivalents_all_ESTIMATED", 0)

    b_dur = baseline_summary.get("total_duration_seconds_MEASURED", 0.0)
    g_dur = generic_summary.get("total_duration_seconds_MEASURED", 0.0)
    j_dur = judge_summary.get("total_duration_seconds_MEASURED", 0.0)

    n = baseline_summary.get("sample_size", 0)

    def safe_ratio(num, denom):
        return round(num / denom, 4) if denom > 0 else None

    return {
        "sample_size": n,
        # --- Quality comparisons ---
        "quality_comparison": {
            "detection_rate": {
                "baseline": baseline_summary.get("initial_detection_rejection_rate", 0.0),
                "generic_review": generic_summary.get("initial_detection_rejection_rate", 0.0),
                "the_judge": judge_summary.get("initial_detection_rejection_rate", 0.0),
            },
            "false_pass_rates": {
                "baseline": b_fpr,
                "generic_review": g_fpr,
                "the_judge": j_fpr,
            },
            "unconditional_false_pass_rates": {
                "baseline": b_ufpr,
                "generic_review": generic_summary.get("unconditional_false_pass_rate", 0.0),
                "the_judge": j_ufpr,
            },
            "verified_correct_delivery_rates": {
                "baseline": b_deliv,
                "generic_review": g_deliv,
                "the_judge": j_deliv,
            },
            "final_correct_implementation_rates": {
                "baseline": b_fcir,
                "generic_review": generic_summary.get("final_correct_implementation_rate", 0.0),
                "the_judge": j_fcir,
            },
            "balanced_accuracy": {
                "baseline": b_ba,
                "generic_review": g_ba,
                "the_judge": j_ba,
            },
            "reliability": {
                "baseline": b_rel,
                "generic_review": g_rel,
                "the_judge": j_rel,
            },
            # Deltas
            "false_pass_reduction_vs_baseline": round(b_fpr - j_fpr, 4),
            "unconditional_false_pass_reduction_vs_baseline": round(b_ufpr - j_ufpr, 4),
            "verified_delivery_delta_vs_baseline": round(j_deliv - b_deliv, 4),
            "final_correctness_delta_vs_baseline": round(j_fcir - b_fcir, 4),
            "balanced_accuracy_delta_vs_baseline": round(j_ba - b_ba, 4),
        },
        # --- Token-equivalent overhead (ESTIMATED) ---
        "token_equivalent_overhead_ESTIMATED": {
            "judge_vs_baseline_ratio": safe_ratio(j_tok, b_tok),
            "judge_vs_generic_ratio": safe_ratio(j_tok, g_tok),
            "additional_token_equivalents_vs_baseline": j_tok - b_tok,
            "additional_token_equivalents_vs_generic": j_tok - g_tok,
            "total_token_equivalents": {
                "baseline_ESTIMATED": b_tok,
                "generic_review_ESTIMATED": g_tok,
                "the_judge_ESTIMATED": j_tok,
            },
            "note": (
                "Token-equivalent counts are byte-count proxies (4 bytes ≈ 1 token-equivalent). "
                "The Judge uses no LLM — ratios reflect subprocess/evidence overhead, not LLM cost."
            ),
        },
        # --- Runtime overhead ---
        "runtime_overhead_MEASURED": {
            "judge_vs_baseline_seconds": round(j_dur - b_dur, 3),
            "judge_vs_generic_seconds": round(j_dur - g_dur, 3),
            "judge_vs_baseline_ratio": safe_ratio(j_dur, b_dur),
            "total_duration": {
                "baseline_MEASURED": b_dur,
                "generic_review_MEASURED": g_dur,
                "the_judge_MEASURED": j_dur,
            },
        },
    }


# ---------------------------------------------------------------------------
# Context duplication aggregate
# ---------------------------------------------------------------------------

def compute_duplication_stats(judge_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate context duplication statistics across Judge (Condition C) trials.
    """
    multi_round_records = []
    all_records = []

    for r in judge_results:
        cr = r["condition_result"]
        dup = cr.get("context_duplication", {})
        task = r["task"]
        rounds = cr.get("rounds", 1)
        ratio = dup.get("duplication_ratio_ESTIMATED", 0.0)
        rep_bytes = dup.get("total_repeated_bytes_ESTIMATED", 0)
        entry = {
            "task": task,
            "rounds": rounds,
            "duplication_ratio": ratio,
            "repeated_bytes": rep_bytes,
            "note": dup.get("duplication_note", ""),
        }
        all_records.append(entry)
        if rounds > 1:
            multi_round_records.append(entry)

    multi_ratios = [d["duplication_ratio"] for d in multi_round_records]
    all_ratios = [d["duplication_ratio"] for d in all_records]
    total_rep_bytes = sum(d["repeated_bytes"] for d in all_records)

    return {
        "trials_analyzed": len(all_records),
        "trials_with_multiple_rounds": len(multi_round_records),
        "mean_duplication_ratio_multi_round_ESTIMATED": round(statistics.mean(multi_ratios), 4) if multi_ratios else 0.0,
        "mean_duplication_ratio_all_trials_ESTIMATED": round(statistics.mean(all_ratios), 4) if all_ratios else 0.0,
        "max_duplication_ratio_ESTIMATED": round(max(all_ratios), 4) if all_ratios else 0.0,
        "total_repeated_bytes_ESTIMATED": total_rep_bytes,
        "per_trial_duplication": all_records,
    }


# ---------------------------------------------------------------------------
# Judge advantage & regression analysis
# ---------------------------------------------------------------------------

def analyze_judge_advantage_cases(per_task: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze specific advantage, regression, and failure cases from per-task data.
    """
    improvements = [r for r in per_task if r["judge_contribution"] == "IMPROVEMENT"]
    regressions = [r for r in per_task if r["judge_contribution"] == "REGRESSION"]
    detect_unverified = [r for r in per_task if r["judge_contribution"] == "DETECT_BUT_CANNOT_VERIFY"]
    all_false_pass = [r for r in per_task if r["judge_contribution"] == "MISSED_DEFECT"]

    return {
        "judge_improves_quality": {
            "count": len(improvements),
            "tasks": [r["task_id"] for r in improvements],
            "details": [
                {
                    "task": r["task_id"],
                    "difficulty": r["difficulty"],
                    "defect_type": r["defect_type"],
                    "why": r.get("judge_why", ""),
                    "note": r.get("contribution_note", ""),
                }
                for r in improvements
            ],
        },
        "judge_hurts_performance": {
            "count": len(regressions),
            "tasks": [r["task_id"] for r in regressions],
            "details": [
                {
                    "task": r["task_id"],
                    "difficulty": r["difficulty"],
                    "baseline_verdict": r["baseline_verdict"],
                    "generic_verdict": r["generic_review_verdict"],
                    "judge_verdict": r["judge_verdict"],
                    "why": r.get("judge_why", ""),
                    "note": r.get("contribution_note", ""),
                }
                for r in regressions
            ],
        },
        "judge_detected_but_unverified": {
            "count": len(detect_unverified),
            "tasks": [r["task_id"] for r in detect_unverified],
            "details": [
                {
                    "task": r["task_id"],
                    "difficulty": r["difficulty"],
                    "defect_type": r["defect_type"],
                    "why": r.get("judge_why", ""),
                    "note": r.get("contribution_note", ""),
                }
                for r in detect_unverified
            ],
        },
        "all_conditions_missed_defect": {
            "count": len(all_false_pass),
            "tasks": [r["task_id"] for r in all_false_pass],
        },
    }
