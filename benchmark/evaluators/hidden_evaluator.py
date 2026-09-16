import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List


def evaluate_hidden_tests(task_dir: str) -> Dict[str, Any]:
    """Execute hidden test suite independently of agent and Judge engine.

    Returns ground truth evaluation dictionary.
    """
    hidden_dir = os.path.join(task_dir, "hidden_tests")
    if not os.path.exists(hidden_dir):
        return {
            "exit_code": -1,
            "ground_truth_verdict": "ERROR",
            "passed_count": 0,
            "failed_count": 0,
            "total_count": 0,
            "stdout": "",
            "stderr": f"Hidden test directory '{hidden_dir}' does not exist.",
        }

    cmd = [sys.executable, "-m", "pytest", "-vv", hidden_dir]
    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=task_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        elapsed = time.time() - start_time
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except Exception as e:
        return {
            "exit_code": -1,
            "ground_truth_verdict": "ERROR",
            "passed_count": 0,
            "failed_count": 0,
            "total_count": 0,
            "stdout": "",
            "stderr": str(e),
        }

    passed_count = 0
    failed_count = 0
    for line in (stdout + "\n" + stderr).splitlines():
        if " PASSED" in line:
            passed_count += 1
        elif " FAILED" in line:
            failed_count += 1

    total_count = passed_count + failed_count
    ground_truth_verdict = "PASS" if (exit_code == 0 and failed_count == 0) else "FAIL"

    return {
        "exit_code": exit_code,
        "ground_truth_verdict": ground_truth_verdict,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "total_count": total_count,
        "execution_time_seconds": round(elapsed, 2),
        "stdout": stdout,
        "stderr": stderr,
    }


def classify_outcome(condition_verdict: str, ground_truth_verdict: str) -> Dict[str, Any]:
    """Classify trial result into signal detection metrics: TP, FP, TN, FN, ABSTAIN."""
    claim_pass = (condition_verdict == "PASS")
    claim_fail = (condition_verdict == "FAIL")
    claim_abstain = (condition_verdict in ("ABSTAIN", "HUMAN_REVIEW_REQUIRED"))

    gt_pass = (ground_truth_verdict == "PASS")

    if claim_pass and gt_pass:
        classification = "TRUE_PASS"  # TP
    elif claim_pass and not gt_pass:
        classification = "FALSE_PASS"  # FP (Unearned PASS!)
    elif claim_fail and not gt_pass:
        classification = "TRUE_FAIL"  # TN
    elif claim_fail and gt_pass:
        classification = "FALSE_FAIL"  # FN
    elif claim_abstain:
        classification = "ABSTAIN"  # ABSTAIN (Refuses decision due to insufficient evidence)
    else:
        classification = "UNKNOWN"

    return {
        "classification": classification,
        "is_true_pass": (classification == "TRUE_PASS"),
        "is_false_pass": (classification == "FALSE_PASS"),
        "is_true_fail": (classification == "TRUE_FAIL"),
        "is_false_fail": (classification == "FALSE_FAIL"),
        "is_abstain": (classification == "ABSTAIN"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Independent Hidden Test Evaluator")
    parser.add_argument("--task-dir", required=True, help="Path to task workspace directory")
    parser.add_argument("--claim-verdict", default="PASS", help="Claim verdict from condition (PASS/FAIL/ABSTAIN)")
    parser.add_argument("--output", default=None, help="Output JSON result file")
    args = parser.parse_args()

    res = evaluate_hidden_tests(args.task_dir)
    class_res = classify_outcome(args.claim_verdict, res["ground_truth_verdict"])
    res.update(class_res)

    print(f"[Hidden Evaluator] Ground Truth Verdict : {res['ground_truth_verdict']}")
    print(f"[Hidden Evaluator] Condition Claim      : {args.claim_verdict}")
    print(f"[Hidden Evaluator] Classification       : {res['classification']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
