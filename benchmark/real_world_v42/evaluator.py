import os
import sys
import json
import shutil
import tempfile
import importlib.util
from pathlib import Path

# Ensure root projects path is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from the_judge.api import verify
from the_judge.core.contract_parser import ContractParser
from the_judge.core.contract_engine import ContractEngine

TASKS_DIR = os.path.join(PROJECT_ROOT, "benchmark", "real_world_v42", "tasks")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "benchmark", "results")
TRAJECTORIES_DIR = os.path.join(PROJECT_ROOT, "benchmark", "real_world_v42", "trajectories")

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(TRAJECTORIES_DIR, exist_ok=True)

def run_hidden_evaluator(workspace_dir: str, task_name: str) -> bool:
    """Run hidden ground truth evaluator in workspace directory."""
    eval_script = os.path.join(workspace_dir, "hidden_evaluator.py")
    if not os.path.exists(eval_script):
        return False
    
    spec = importlib.util.spec_from_file_location("hidden_evaluator", eval_script)
    mod = importlib.util.module_from_spec(spec)
    
    # Save current path and add workspace
    orig_path = list(sys.path)
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)
        
    try:
        spec.loader.exec_module(mod)
        if hasattr(mod, "evaluate"):
            res = mod.evaluate()
            return bool(res)
        return True
    except Exception as e:
        return False
    finally:
        sys.path = orig_path

def evaluate_task_under_conditions(task_id: str):
    """Run CONTROL, JUDGE_V40, and JUDGE_V42 on a specific task."""
    task_dir = os.path.join(TASKS_DIR, task_id)
    with open(os.path.join(task_dir, "task_spec.json"), "r", encoding="utf-8") as f:
        spec = json.load(f)
        
    task_name = spec["name"]
    
    # Read code variants
    with open(os.path.join(task_dir, "initial_code.py"), "r", encoding="utf-8") as f:
        initial_code = f.read()
    with open(os.path.join(task_dir, "repaired_code.py"), "r", encoding="utf-8") as f:
        repaired_code = f.read()
        
    results = {
        "task_id": task_id,
        "name": task_name,
        "control": {},
        "judge_v40": {},
        "judge_v42": {},
        "ablation": {},
        "adversarial": {}
    }
    
    # Evaluate repaired_code (representing final implementation state)
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Save code as module file
        target_file = os.path.join(tmp_dir, f"{task_name}.py")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(repaired_code)
            
        # Copy hidden evaluator
        shutil.copy(os.path.join(task_dir, "hidden_evaluator.py"), os.path.join(tmp_dir, "hidden_evaluator.py"))
        
        # 1. Ground Truth
        ground_truth_pass = run_hidden_evaluator(tmp_dir, task_name)
        results["control"]["ground_truth_pass"] = ground_truth_pass
        results["control"]["decision"] = "PASS" if ground_truth_pass else "FAIL"
        
        # 2. Judge v4.0 (No task spec / No contract engine enforcement)
        res_v40 = verify(tmp_dir, task_spec=None)
        results["judge_v40"]["decision"] = res_v40.decision
        results["judge_v40"]["trust_profile"] = res_v40.trust_profile
        
        # Determine false PASS / false FAIL for v4.0
        is_false_pass_v40 = (res_v40.decision == "PASS" and not ground_truth_pass)
        is_false_fail_v40 = (res_v40.decision == "FAIL" and ground_truth_pass)
        results["judge_v40"]["false_pass"] = is_false_pass_v40
        results["judge_v40"]["false_fail"] = is_false_fail_v40

        # 3. Judge v4.2 (With explicit task contract & contract engine)
        res_v42 = verify(tmp_dir, task_spec=spec)
        results["judge_v42"]["decision"] = res_v42.decision
        results["judge_v42"]["trust_profile"] = res_v42.trust_profile
        
        # Determine false PASS / false FAIL for v4.2
        is_false_pass_v42 = (res_v42.decision == "PASS" and not ground_truth_pass)
        is_false_fail_v42 = (res_v42.decision == "FAIL" and ground_truth_pass)
        results["judge_v42"]["false_pass"] = is_false_pass_v42
        results["judge_v42"]["false_fail"] = is_false_fail_v42
        
        # Extract coverage metrics
        spec_cov = res_v42.trust_profile.get("specification_coverage", {})
        results["judge_v42"]["critical_coverage_pct"] = spec_cov.get("critical_coverage_pct", 0.0)
        results["judge_v42"]["overall_coverage_pct"] = spec_cov.get("overall_coverage_pct", 0.0)
        results["judge_v42"]["unverified_rate_pct"] = spec_cov.get("unverified_rate_pct", 0.0)
        results["judge_v42"]["specification_escape"] = (not ground_truth_pass and spec_cov.get("unverified_count", 0) > 0)
        
        # 4. Ablation Study Conditions:
        # A: No contract
        res_ablation_a = verify(tmp_dir, task_spec=None)
        # B: Explicit human contract
        res_ablation_b = res_v42
        # C: Automatically extracted contract from description
        parser = ContractParser()
        parsed_res = parser.parse_natural_language_spec(spec.get("description", ""))
        extracted_contract = {"requirements": parsed_res.get("parsed_requirements", [])}
        res_ablation_c = verify(tmp_dir, task_spec=extracted_contract)
        
        results["ablation"]["condition_a_no_contract"] = res_ablation_a.decision
        results["ablation"]["condition_b_explicit_contract"] = res_ablation_b.decision
        results["ablation"]["condition_c_extracted_contract"] = res_ablation_c.decision
        
    return results

def run_all_evaluations():
    """Run full benchmark across all 20 tasks and export reports."""
    task_dirs = sorted([d for d in os.listdir(TASKS_DIR) if os.path.isdir(os.path.join(TASKS_DIR, d))])
    
    all_results = []
    print(f"--- Running v4.2 Benchmark on {len(task_dirs)} tasks ---")
    
    for t_id in task_dirs:
        res = evaluate_task_under_conditions(t_id)
        all_results.append(res)
        gt = res["control"]["decision"]
        v40 = res["judge_v40"]["decision"]
        v42 = res["judge_v42"]["decision"]
        print(f"Task {t_id:30s} | GT: {gt:4s} | v4.0: {v40:7s} | v4.2: {v42:7s}")

    # Compute Summary Statistics
    total_tasks = len(all_results)
    
    # Ground Truth Success (Control)
    control_pass_count = sum(1 for r in all_results if r["control"]["ground_truth_pass"])
    
    # v4.0 metrics
    v40_pass_count = sum(1 for r in all_results if r["judge_v40"]["decision"] == "PASS")
    v40_false_pass = sum(1 for r in all_results if r["judge_v40"]["false_pass"])
    v40_false_fail = sum(1 for r in all_results if r["judge_v40"]["false_fail"])
    v40_abstain = sum(1 for r in all_results if r["judge_v40"]["decision"] == "ABSTAIN")
    
    # v4.2 metrics
    v42_pass_count = sum(1 for r in all_results if r["judge_v42"]["decision"] == "PASS")
    v42_false_pass = sum(1 for r in all_results if r["judge_v42"]["false_pass"])
    v42_false_fail = sum(1 for r in all_results if r["judge_v42"]["false_fail"])
    v42_abstain = sum(1 for r in all_results if r["judge_v42"]["decision"] == "ABSTAIN")
    
    # Coverage averages
    avg_critical_cov = sum(r["judge_v42"]["critical_coverage_pct"] for r in all_results) / total_tasks
    avg_overall_cov = sum(r["judge_v42"]["overall_coverage_pct"] for r in all_results) / total_tasks
    
    # Specification Escape Rate
    gt_fail_count = total_tasks - control_pass_count
    spec_escapes = sum(1 for r in all_results if r["judge_v42"]["specification_escape"])
    spec_escape_rate = (spec_escapes / gt_fail_count * 100.0) if gt_fail_count > 0 else 0.0

    print("\n================ BENCHMARK SUMMARY ================")
    print(f"Total Tasks:                      {total_tasks}")
    print(f"Ground Truth Correct Implementations: {control_pass_count}/{total_tasks} ({control_pass_count/total_tasks*100:.1f}%)")
    print(f"v4.0 False PASS Rate:            {v40_false_pass}/{total_tasks} ({v40_false_pass/total_tasks*100:.1f}%)")
    print(f"v4.2 False PASS Rate:            {v42_false_pass}/{total_tasks} ({v42_false_pass/total_tasks*100:.1f}%)")
    print(f"v4.2 ABSTAIN Rate:               {v42_abstain}/{total_tasks} ({v42_abstain/total_tasks*100:.1f}%)")
    print(f"Avg Critical Requirement Coverage: {avg_critical_cov:.1f}%")
    print(f"Avg Overall Requirement Coverage:  {avg_overall_cov:.1f}%")
    print(f"Specification Escape Rate:        {spec_escape_rate:.1f}%")
    print("===================================================\n")

    # Export json files
    with open(os.path.join(RESULTS_DIR, "v4_2_control.json"), "w") as f:
        json.dump({"total_tasks": total_tasks, "ground_truth_passed": control_pass_count, "results": [r["control"] for r in all_results]}, f, indent=2)
        
    with open(os.path.join(RESULTS_DIR, "v4_2_judge_v40.json"), "w") as f:
        json.dump({"total_tasks": total_tasks, "false_pass_count": v40_false_pass, "results": [r["judge_v40"] for r in all_results]}, f, indent=2)

    with open(os.path.join(RESULTS_DIR, "v4_2_judge_v42.json"), "w") as f:
        json.dump({
            "total_tasks": total_tasks,
            "ground_truth_pass_count": control_pass_count,
            "v42_pass_count": v42_pass_count,
            "v42_false_pass_count": v42_false_pass,
            "v42_false_fail_count": v42_false_fail,
            "v42_abstain_count": v42_abstain,
            "avg_critical_coverage_pct": avg_critical_cov,
            "avg_overall_coverage_pct": avg_overall_cov,
            "specification_escape_rate_pct": spec_escape_rate,
            "results": [r["judge_v42"] for r in all_results]
        }, f, indent=2)

    with open(os.path.join(RESULTS_DIR, "v4_2_ablation.json"), "w") as f:
        json.dump({"results": [r["ablation"] for r in all_results]}, f, indent=2)

    with open(os.path.join(RESULTS_DIR, "v4_2_forensics.json"), "w") as f:
        forensics = []
        for r in all_results:
            forensics.append({
                "task_id": r["task_id"],
                "ground_truth_pass": r["control"]["ground_truth_pass"],
                "v40_decision": r["judge_v40"]["decision"],
                "v42_decision": r["judge_v42"]["decision"],
                "v40_false_pass": r["judge_v40"]["false_pass"],
                "v42_false_pass": r["judge_v42"]["false_pass"],
                "specification_escape": r["judge_v42"]["specification_escape"]
            })
        json.dump(forensics, f, indent=2)

if __name__ == "__main__":
    run_all_evaluations()
