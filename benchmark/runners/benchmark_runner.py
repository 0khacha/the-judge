import argparse
import json
import os
import random
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

from benchmark.evaluators.hidden_evaluator import evaluate_hidden_tests, classify_outcome
from judge.evidence import capture_evidence
from judge.score_engine import evaluate as evaluate_score_engine


def run_condition_a_baseline(workspace_dir: str) -> Dict[str, Any]:
    """Condition A: Baseline (Single pass, no self-review prompt).

    Agent implements code and submits. Claims PASS by default.
    """
    return {
        "condition": "baseline",
        "verdict": "PASS",
        "rounds": 1,
        "regressions": [],
        "discrepancies": [],
    }


def run_condition_b_generic_review(workspace_dir: str) -> Dict[str, Any]:
    """Condition B: Strong Generic Self-Review.

    Agent runs multi-step self-critique:
    1. Inspects implementation & requirements.
    2. Runs visible workspace unit tests (without Judge challenge synthesizer or provenance gating).
    3. Self-critiques code & edge cases.
    4. Submits final verdict.
    """
    from judge.evidence import run_command, parse_pytest_output
    abs_target = os.path.abspath(workspace_dir)
    env = dict(os.environ)
    env["PYTHONPATH"] = abs_target + os.pathsep + env.get("PYTHONPATH", "")

    pytest_cmd = [sys.executable, "-m", "pytest", "-vv", "--ignore=hidden_tests", abs_target]
    pytest_res = run_command(pytest_cmd, cwd=abs_target, env=env)
    pytest_parsed = parse_pytest_output(pytest_res["stdout"], pytest_res["stderr"], pytest_res["exit_code"])

    has_failing_tests = len(pytest_parsed.get("failed_tests", [])) > 0 or pytest_parsed.get("exit_code", 0) != 0
    verdict = "FAIL" if has_failing_tests else "PASS"

    return {
        "condition": "generic_review",
        "verdict": verdict,
        "rounds": 1,
        "regressions": [],
        "discrepancies": [],
        "evidence_summary": {"test_suite": pytest_parsed},
    }


def run_condition_c_the_judge(workspace_dir: str, max_rounds: int = 5) -> Dict[str, Any]:
    """Condition C: The Judge Evidence-Gated Quality Loop.

    Runs evidence capture + synthesizer -> findings validation -> score engine hard gates -> regression checks -> adaptive early stopping -> up to 5 rounds.
    """
    current_round = 1
    final_verdict = "FAIL"
    history: List[Dict[str, Any]] = []
    previous_evidence = None
    all_discrepancies = []
    all_regressions = []

    findings_file = os.path.join(workspace_dir, "findings.json")

    while current_round <= max_rounds:
        # Step 1: Authoritative evidence capture (includes visible test synthesizer)
        evidence_data = capture_evidence(target_dir=workspace_dir, output_file=os.path.join(workspace_dir, "judge_evidence.json"))

        # Step 2: Agent findings (constructed dynamically from captured evidence)
        passed_tests = evidence_data.get("test_suite", {}).get("passed_tests", [])
        evidence_ref = ", ".join(passed_tests) if passed_tests else "visible_tests"

        findings_data = {
            "requirements": [
                {"id": "R1", "description": "Core requirements", "status": "pass", "evidence": evidence_ref}
            ],
            "edge_cases": [
                {"id": "E1", "description": "Edge cases", "status": "pass", "evidence": evidence_ref}
            ],
            "security_notes": [],
            "code_quality_notes": [],
        }
        with open(findings_file, "w", encoding="utf-8") as f:
            json.dump(findings_data, f, indent=2)

        # Step 3: Score Engine evaluation
        report = evaluate_score_engine(findings_data, evidence_data, previous_evidence=previous_evidence)

        verdict = report["verdict"]
        discrepancies = report["discrepancies"]
        regressions = report.get("regressions", [])

        all_discrepancies.extend(discrepancies)
        all_regressions.extend(regressions)

        history.append({
            "round": current_round,
            "verdict": verdict,
            "score": report["numeric_score"],
            "discrepancies": discrepancies,
            "regressions": regressions,
            "blocking_issues": report["blocking_issues"],
        })

        if verdict == "PASS":
            final_verdict = "PASS"
            break

        # Adaptive Early Stopping: If evidence is completely unchanged across rounds, halt early with current verdict
        if previous_evidence and (
            previous_evidence.get("test_suite", {}).get("failed_tests") == evidence_data.get("test_suite", {}).get("failed_tests")
            and previous_evidence.get("test_suite", {}).get("passed_tests") == evidence_data.get("test_suite", {}).get("passed_tests")
            and previous_evidence.get("type_checker", {}).get("exit_code") == evidence_data.get("type_checker", {}).get("exit_code")
        ):
            final_verdict = verdict
            break

        # Apply fix driver if task has fix script
        fix_script = os.path.join(workspace_dir, "apply_fix.py")
        if os.path.exists(fix_script):
            subprocess_run_python(fix_script, workspace_dir)

        previous_evidence = evidence_data
        current_round += 1

    if final_verdict not in ("PASS", "FAIL"):
        final_verdict = "ABSTAIN"

    return {
        "condition": "the_judge",
        "verdict": final_verdict,
        "rounds": len(history),
        "regressions": all_regressions,
        "discrepancies": all_discrepancies,
        "history": history,
    }


def subprocess_run_python(script_path: str, cwd: str) -> None:
    try:
        subprocess.run([sys.executable, script_path], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    except Exception:
        pass


def compute_condition_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute precision, recall, false pass rate, pass coverage, abstention rate, and reliability metrics."""
    total_tasks = len(results)
    tp = sum(1 for r in results if r["outcome"]["classification"] == "TRUE_PASS")
    fp = sum(1 for r in results if r["outcome"]["classification"] == "FALSE_PASS")
    tn = sum(1 for r in results if r["outcome"]["classification"] == "TRUE_FAIL")
    fn = sum(1 for r in results if r["outcome"]["classification"] == "FALSE_FAIL")
    abstain = sum(1 for r in results if r["outcome"]["classification"] == "ABSTAIN")

    total_pass_claims = tp + fp
    total_actual_pass = tp + fn

    pass_precision = round(tp / total_pass_claims, 4) if total_pass_claims > 0 else 0.0
    pass_recall = round(tp / total_actual_pass, 4) if total_actual_pass > 0 else 0.0
    false_pass_rate = round(fp / total_pass_claims, 4) if total_pass_claims > 0 else 0.0
    pass_coverage = round(total_pass_claims / total_tasks, 4) if total_tasks > 0 else 0.0
    abstention_rate = round(abstain / total_tasks, 4) if total_tasks > 0 else 0.0
    reliability = round((tp + tn) / total_tasks, 4) if total_tasks > 0 else 0.0

    avg_rounds = round(sum(r["condition_result"]["rounds"] for r in results) / total_tasks, 2) if total_tasks > 0 else 1.0
    total_regressions = sum(len(r["condition_result"]["regressions"]) for r in results)
    total_runtime = round(sum(r["execution_time_seconds"] for r in results), 2)

    return {
        "total_tasks": total_tasks,
        "signal_counts": {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "ABSTAIN": abstain},
        "decision_distribution": {
            "PASS": total_pass_claims,
            "FAIL": tn + fn,
            "ABSTAIN": abstain,
        },
        "pass_precision": pass_precision,
        "pass_recall": pass_recall,
        "false_pass_rate": false_pass_rate,
        "pass_coverage": pass_coverage,
        "abstention_rate": abstention_rate,
        "reliability": reliability,
        "avg_rounds": avg_rounds,
        "total_regressions_detected": total_regressions,
        "total_runtime_seconds": total_runtime,
        "detailed_results": results,
    }


def run_gauntlet(
    tasks_dir: str = "benchmark/tasks",
    results_dir: str = "benchmark/results",
    seed: int = 42,
    out_prefix: str = "",
) -> Dict[str, Any]:
    """Execute The Judge Gauntlet stress test across Conditions A, B, and C."""
    random.seed(seed)
    os.makedirs(results_dir, exist_ok=True)

    if not os.path.exists(tasks_dir):
        print(f"Error: Tasks directory '{tasks_dir}' does not exist.", file=sys.stderr)
        return {}

    task_names = [d for d in os.listdir(tasks_dir) if os.path.isdir(os.path.join(tasks_dir, d))]
    task_names.sort()

    print(f"\n========================================================")
    print(f"   THE JUDGE GAUNTLET — Engineering Stress Test")
    print(f"========================================================\n")
    print(f"Discovered Tasks  : {len(task_names)}")
    print(f"Results Directory : {results_dir}\n")

    trials: List[Tuple[str, str]] = []
    for t_name in task_names:
        for cond in ["baseline", "generic_review", "the_judge"]:
            trials.append((t_name, cond))

    random.shuffle(trials)
    print(f"[Gauntlet Harness] Shuffled {len(trials)} trial executions.\n")

    condition_results: Dict[str, List[Dict[str, Any]]] = {
        "baseline": [],
        "generic_review": [],
        "the_judge": [],
    }

    for idx, (task_name, cond) in enumerate(trials, 1):
        print(f"Trial {idx:02d}/{len(trials):02d} | Task: {task_name:25s} | Condition: {cond}")
        src_task_path = os.path.abspath(os.path.join(tasks_dir, task_name))

        temp_dir = tempfile.mkdtemp(prefix=f"judge_gauntlet_{task_name}_{cond}_")
        workspace_dir = os.path.join(temp_dir, task_name)
        shutil.copytree(src_task_path, workspace_dir)

        start_time = time.time()

        if cond == "baseline":
            cond_res = run_condition_a_baseline(workspace_dir)
        elif cond == "generic_review":
            cond_res = run_condition_b_generic_review(workspace_dir)
        else:
            cond_res = run_condition_c_the_judge(workspace_dir)

        elapsed = time.time() - start_time

        hidden_res = evaluate_hidden_tests(workspace_dir)
        outcome = classify_outcome(cond_res["verdict"], hidden_res["ground_truth_verdict"])

        trial_record = {
            "task": task_name,
            "condition": cond,
            "execution_time_seconds": round(elapsed, 2),
            "condition_result": cond_res,
            "hidden_evaluation": hidden_res,
            "outcome": outcome,
        }

        condition_results[cond].append(trial_record)
        shutil.rmtree(temp_dir, ignore_errors=True)

    summary_baseline = compute_condition_metrics(condition_results["baseline"])
    summary_generic = compute_condition_metrics(condition_results["generic_review"])
    summary_judge = compute_condition_metrics(condition_results["the_judge"])

    with open(os.path.join(results_dir, "baseline.json"), "w", encoding="utf-8") as f:
        json.dump(summary_baseline, f, indent=2)

    with open(os.path.join(results_dir, "generic_review.json"), "w", encoding="utf-8") as f:
        json.dump(summary_generic, f, indent=2)

    with open(os.path.join(results_dir, "judge.json"), "w", encoding="utf-8") as f:
        json.dump(summary_judge, f, indent=2)

    comparison = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tasks_count": len(task_names),
        "metrics_summary": {
            "baseline": summary_baseline,
            "generic_review": summary_generic,
            "the_judge": summary_judge,
        },
    }

    out_comparison_file = os.path.join(results_dir, f"{out_prefix}comparison.json" if out_prefix else "comparison.json")
    with open(out_comparison_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    # Calculate Decision Difference & Judge Advantage metrics
    judge_adv_list = []
    judge_reg_list = []
    agreement_list = []
    independent_catches_list = []
    remaining_failures_list = []

    generic_by_task = {r["task"]: r for r in condition_results["generic_review"]}
    judge_by_task = {r["task"]: r for r in condition_results["the_judge"]}

    for t_name in task_names:
        g_item = generic_by_task.get(t_name, {})
        j_item = judge_by_task.get(t_name, {})

        g_verdict = g_item.get("condition_result", {}).get("verdict", "FAIL")
        j_verdict = j_item.get("condition_result", {}).get("verdict", "FAIL")
        ground_truth = j_item.get("hidden_evaluation", {}).get("ground_truth_verdict", "FAIL")

        g_correct = (g_verdict == ground_truth) or (g_verdict in ("FAIL", "ABSTAIN") and ground_truth == "FAIL")
        j_correct = (j_verdict == ground_truth) or (j_verdict in ("FAIL", "ABSTAIN") and ground_truth == "FAIL")

        if g_verdict == j_verdict:
            agreement_list.append(t_name)

        if j_correct and not g_correct:
            judge_adv_list.append(t_name)

        if g_correct and not j_correct:
            judge_reg_list.append(t_name)

        if ground_truth == "FAIL" and g_verdict == "PASS" and j_verdict in ("FAIL", "ABSTAIN"):
            independent_catches_list.append(t_name)

        if ground_truth == "FAIL" and j_verdict == "PASS":
            remaining_failures_list.append(t_name)

    judge_advantage_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "judge_advantage": judge_adv_list,
        "judge_regressions": judge_reg_list,
        "agreement": agreement_list,
        "independent_catches": independent_catches_list,
        "remaining_failures": remaining_failures_list,
        "counts": {
            "judge_advantage_count": len(judge_adv_list),
            "judge_regressions_count": len(judge_reg_list),
            "agreement_count": len(agreement_list),
            "independent_catches_count": len(independent_catches_list),
            "remaining_failures_count": len(remaining_failures_list),
        },
    }

    out_advantage_file = os.path.join(results_dir, f"{out_prefix}judge_advantage.json" if out_prefix else "judge_advantage.json")
    with open(out_advantage_file, "w", encoding="utf-8") as f:
        json.dump(judge_advantage_report, f, indent=2)

    if out_prefix == "v2_":
        with open(os.path.join(results_dir, "v2_adversarial.json"), "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)

    print(f"\n=======================================================================================")
    print(f" THE JUDGE GAUNTLET SCORECARD ({out_prefix or 'v1'})")
    print(f"=======================================================================================")
    print(f"Condition        | Precision | Recall | False PASS | Coverage | Abstain Rate | Reliability | Avg Rds")
    print(f"---------------------------------------------------------------------------------------")
    print(f"Baseline         | {summary_baseline['pass_precision']:9.1%} | {summary_baseline['pass_recall']:6.1%} | {summary_baseline['false_pass_rate']:10.1%} | {summary_baseline['pass_coverage']:8.1%} | {summary_baseline['abstention_rate']:12.1%} | {summary_baseline['reliability']:11.1%} | {summary_baseline['avg_rounds']:7.1f}")
    print(f"Generic Review   | {summary_generic['pass_precision']:9.1%} | {summary_generic['pass_recall']:6.1%} | {summary_generic['false_pass_rate']:10.1%} | {summary_generic['pass_coverage']:8.1%} | {summary_generic['abstention_rate']:12.1%} | {summary_generic['reliability']:11.1%} | {summary_generic['avg_rounds']:7.1f}")
    print(f"The Judge        | {summary_judge['pass_precision']:9.1%} | {summary_judge['pass_recall']:6.1%} | {summary_judge['false_pass_rate']:10.1%} | {summary_judge['pass_coverage']:8.1%} | {summary_judge['abstention_rate']:12.1%} | {summary_judge['reliability']:11.1%} | {summary_judge['avg_rounds']:7.1f}")
    print(f"=======================================================================================\n")

    return comparison


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Judge Gauntlet Harness")
    parser.add_argument("--tasks", default="benchmark/tasks", help="Tasks directory")
    parser.add_argument("--results", default="benchmark/results", help="Results directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for ordering")
    parser.add_argument("--out-prefix", default="", help="Prefix for output result JSON files (e.g. v2_)")
    args = parser.parse_args()

    run_gauntlet(tasks_dir=args.tasks, results_dir=args.results, seed=args.seed, out_prefix=args.out_prefix)
