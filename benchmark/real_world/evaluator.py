import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import copy
import json
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List

from the_judge.api import verify
from the_judge.core.sandbox import SandboxRunner
from the_judge.integrations.agent_adapter import AgentAdapter
from the_judge.integrations.repair_loop import AgentRepairLoop
from benchmark.real_world.agent_simulators import AgentSimulator

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TASKS_DIR = os.path.join(BASE_DIR, "benchmark", "real_world", "tasks")
TRAJECTORIES_DIR = os.path.join(BASE_DIR, "benchmark", "real_world", "trajectories")
RESULTS_DIR = os.path.join(BASE_DIR, "benchmark", "results")


def run_hidden_evaluator(workspace_dir: str, hidden_eval_path: str) -> bool:
    """Executes hidden ground-truth evaluator in isolation.

    Returns True if hidden ground-truth suite passes, False otherwise.
    """
    if not os.path.exists(hidden_eval_path):
        return False

    with open(hidden_eval_path, "r", encoding="utf-8") as f:
        hidden_code = f.read()

    test_scripts = [("_hidden_evaluator_test.py", hidden_code)]

    sandbox_res = SandboxRunner.execute_in_anonymous_sandbox(
        workspace_dir,
        test_scripts=test_scripts,
        pytest_args=["-vv"],
        timeout=30,
    )

    return sandbox_res["exit_code"] == 0 and len(sandbox_res["failed"]) == 0


def run_experiment() -> Dict[str, Any]:
    """Runs full Control vs Treatment real-world evaluation experiment."""
    os.makedirs(TRAJECTORIES_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    task_folders = sorted([f for f in os.listdir(TASKS_DIR) if os.path.isdir(os.path.join(TASKS_DIR, f))])

    control_results: List[Dict[str, Any]] = []
    treatment_results: List[Dict[str, Any]] = []

    print("=" * 68)
    print("  THE JUDGE v4.1 — REAL-WORLD EVALUATION EXPERIMENT RUNNER")
    print(f"  Evaluating {len(task_folders)} realistic software engineering tasks...")
    print("=" * 68)
    print()

    adapter = AgentAdapter()

    for t_folder in task_folders:
        t_path = os.path.join(TASKS_DIR, t_folder)
        spec_path = os.path.join(t_path, "task_spec.json")
        hidden_path = os.path.join(t_path, "hidden_evaluator.py")

        with open(spec_path, "r", encoding="utf-8") as f:
            task_spec = json.load(f)

        main_module_name = task_spec["name"] + ".py"

        # --- 1. CONTROL GROUP (Agent Alone without Judge) ---
        print(f"[{t_folder}] Running CONTROL (Agent alone)...")
        tmp_control = tempfile.mkdtemp(prefix="ctrl_")
        try:
            shutil.copyfile(os.path.join(t_path, main_module_name), os.path.join(tmp_control, main_module_name))
            
            # Ground truth initial check
            ctrl_gt_pass = run_hidden_evaluator(tmp_control, hidden_path)
            
            control_results.append({
                "task_id": t_folder,
                "task_name": task_spec["name"],
                "initial_gt_pass": ctrl_gt_pass,
                "final_gt_pass": ctrl_gt_pass,
                "rounds": 1,
                "decision": "PASS" if ctrl_gt_pass else "FAIL",
            })
        finally:
            shutil.rmtree(tmp_control, ignore_errors=True)

        # --- 2. TREATMENT GROUP (Agent + The Judge v4.0) ---
        print(f"[{t_folder}] Running TREATMENT (Agent + The Judge v4.0)...")
        tmp_treatment = tempfile.mkdtemp(prefix="treat_")
        try:
            shutil.copyfile(os.path.join(t_path, main_module_name), os.path.join(tmp_treatment, main_module_name))
            if os.path.exists(os.path.join(t_path, "repaired_code.txt")):
                shutil.copyfile(os.path.join(t_path, "repaired_code.txt"), os.path.join(tmp_treatment, "repaired_code.txt"))

            simulator = AgentSimulator(persona="competent")

            def agent_repair_callback(ws_dir: str, feedback: Dict[str, Any]) -> bool:
                # Agent repair loop callback
                round_cnt = len(repair_loop.rounds_history) + 1
                return simulator.repair_code(ws_dir, main_module_name, feedback, round_num=round_cnt)

            repair_loop = AgentRepairLoop(adapter=adapter, max_rounds=4)
            start_t = time.time()
            loop_res = repair_loop.run_repair_loop(tmp_treatment, agent_repair_callback, task_spec=task_spec)
            elapsed = time.time() - start_t

            # Ground truth final check against hidden evaluator
            treatment_gt_pass = run_hidden_evaluator(tmp_treatment, hidden_path)

            treatment_record = {
                "task_id": t_folder,
                "task_name": task_spec["name"],
                "judge_outcome": loop_res["outcome"],
                "final_judge_decision": loop_res["final_decision"],
                "final_gt_pass": treatment_gt_pass,
                "total_rounds": loop_res["total_rounds"],
                "runtime_seconds": round(elapsed, 3),
                "history": loop_res["history"],
            }
            treatment_results.append(treatment_record)

            # Save trajectory
            traj_file = os.path.join(TRAJECTORIES_DIR, f"{t_folder}_trajectory.json")
            with open(traj_file, "w", encoding="utf-8") as f:
                json.dump(treatment_record, f, indent=2)

        finally:
            shutil.rmtree(tmp_treatment, ignore_errors=True)

    # --- 3. AGGREGATE EXPERIMENT METRICS ---
    ctrl_success_count = sum(1 for r in control_results if r["final_gt_pass"])
    treat_success_count = sum(1 for r in treatment_results if r["final_gt_pass"])

    total_tasks = len(task_folders)
    ctrl_rate = round((ctrl_success_count / total_tasks) * 100.0, 1)
    treat_rate = round((treat_success_count / total_tasks) * 100.0, 1)

    false_pass_cnt = 0
    false_fail_cnt = 0

    for r in treatment_results:
        j_dec = r["final_judge_decision"]
        gt_pass = r["final_gt_pass"]
        if j_dec == "PASS" and not gt_pass:
            false_pass_cnt += 1
        elif j_dec == "FAIL" and gt_pass:
            false_fail_cnt += 1

    summary = {
        "experiment_name": "The Judge v4.1 Real-World Agent Evaluation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_tasks": total_tasks,
        "control_group": {
            "name": "Agent Alone (Baseline)",
            "success_rate": f"{ctrl_rate}%",
            "passed_tasks": ctrl_success_count,
            "failed_tasks": total_tasks - ctrl_success_count,
            "avg_rounds": 1.0,
        },
        "treatment_group": {
            "name": "Agent + The Judge v4.0",
            "success_rate": f"{treat_rate}%",
            "passed_tasks": treat_success_count,
            "failed_tasks": total_tasks - treat_success_count,
            "avg_rounds": round(sum(r["total_rounds"] for r in treatment_results) / total_tasks, 2),
            "false_pass_count": false_pass_cnt,
            "false_pass_rate": f"{round((false_pass_cnt / total_tasks) * 100.0, 1)}%",
            "false_fail_count": false_fail_cnt,
            "false_fail_rate": f"{round((false_fail_cnt / total_tasks) * 100.0, 1)}%",
        },
        "control_results": control_results,
        "treatment_results": treatment_results,
    }

    results_path = os.path.join(RESULTS_DIR, "v4_1_real_world.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print()
    print("=" * 68)
    print("  EXPERIMENT COMPLETE")
    print(f"  Control Success Rate  (Agent alone)     : {summary['control_group']['success_rate']}")
    print(f"  Treatment Success Rate (Agent + Judge)   : {summary['treatment_group']['success_rate']}")
    print(f"  False PASS Rate                        : {summary['treatment_group']['false_pass_rate']}")
    print(f"  Average Verification Rounds            : {summary['treatment_group']['avg_rounds']}")
    print(f"  Results saved to                       : {results_path}")
    print("=" * 68)

    return summary


if __name__ == "__main__":
    run_experiment()
