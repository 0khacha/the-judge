"""
run_agent_abc.py — Real Coding-Agent A/B/C Benchmark Runner.

Executes coding agents across three strictly controlled conditions:
  Condition A — Baseline (standard developer tools, no review directive)
  Condition B — Generic Review (standard developer tools + critical review directive)
  Condition C — The Judge (standard developer tools + judge_verify tool)

Enforces:
  - Real LLM API communication (Anthropic, OpenAI, Gemini)
  - Zero oracle patches: apply_fix.py is physically excluded from agent workspace
  - Physical isolation of hidden tests: hidden_tests/ moved to inaccessible evaluator environment
  - Strict budget equality: exactly max_turns allocated to all conditions
  - Fail closed: If provider credentials are missing or fail, benchmark halts immediately
  - No synthetic tokens: Token accounting extracted strictly from provider responses
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from benchmark.agent.agent_interface import AgentInterface, AgentResult
from benchmark.agent.agent_report_generator import generate_agent_report
from benchmark.agent.llm_agent import LLMAgent
from benchmark.agent.providers.base_provider import AgentProvider
from benchmark.agent.providers.factory import get_provider
from benchmark.agent.test_agent import TestAgent
from benchmark.benchmark_abc.conditions import compute_workspace_hash
from benchmark.benchmark_abc.independent_evaluator import classify_outcome, run_hidden_evaluator
from benchmark.benchmark_abc.task_catalog import TASK_BY_ID

CONDITIONS = ["baseline", "generic_review", "the_judge"]


def run_single_agent_trial(
    task_id: str,
    condition: str,
    tasks_dir: str,
    mode: str,
    provider: AgentProvider,
    model_name: str,
    seed: int,
    run_id: str,
    max_turns: int = 15,
) -> Dict[str, Any]:
    """Execute one agent trial with strict physical isolation and ground-truth evaluation."""
    src_task_path = os.path.abspath(os.path.join(tasks_dir, task_id))
    if not os.path.isdir(src_task_path):
        return {
            "run_id": run_id,
            "task": task_id,
            "condition": condition,
            "error": f"Task directory not found: {src_task_path}",
        }

    temp_base = tempfile.mkdtemp(prefix=f"agent_bench_{task_id}_{condition}_")
    agent_workspace = os.path.join(temp_base, "agent_ws")
    evaluator_workspace = os.path.join(temp_base, "eval_ws")

    try:
        # Copy task files to agent workspace
        shutil.copytree(src_task_path, agent_workspace)
        os.makedirs(evaluator_workspace, exist_ok=True)

        # 1. Physically exclude apply_fix.py from agent workspace
        oracle_file = os.path.join(agent_workspace, "apply_fix.py")
        if os.path.exists(oracle_file):
            os.remove(oracle_file)

        # 2. Physically move hidden_tests/ to evaluator workspace
        src_hidden = os.path.join(agent_workspace, "hidden_tests")
        dst_hidden = os.path.join(evaluator_workspace, "hidden_tests")
        if os.path.exists(src_hidden):
            shutil.move(src_hidden, dst_hidden)

        # Verify physical isolation
        hidden_in_ws = os.path.exists(src_hidden)
        oracle_in_ws = os.path.exists(oracle_file)
        if hidden_in_ws or oracle_in_ws:
            raise PermissionError("Physical workspace isolation failed.")

        # Compute initial pristine workspace hash
        initial_hash = compute_workspace_hash(agent_workspace)

        # Instantiate agent based on mode
        agent: AgentInterface
        agent_type = "llm" if mode == "real" else "test"
        if mode == "real":
            agent = LLMAgent(provider=provider, model_name=model_name)
        else:
            agent = TestAgent(model_name=model_name)

        task_info = TASK_BY_ID.get(task_id, {"task_id": task_id})

        # Run agent
        agent_result: AgentResult = agent.run_task(
            task_info=task_info,
            condition=condition,
            workspace_dir=agent_workspace,
            max_turns=max_turns,
        )

        # Compute final workspace hash
        final_hash = compute_workspace_hash(agent_workspace)

        # 3. Independent Evaluation: Copy final Python source files to evaluator environment
        for root, _, files in os.walk(agent_workspace):
            for f in files:
                if f.endswith(".py"):
                    rel_p = os.path.relpath(os.path.join(root, f), agent_workspace)
                    target_p = os.path.join(evaluator_workspace, rel_p)
                    os.makedirs(os.path.dirname(target_p), exist_ok=True)
                    shutil.copy2(os.path.join(root, f), target_p)

        # Run hidden tests in isolated evaluator workspace
        gt = run_hidden_evaluator(evaluator_workspace)
        outcome = classify_outcome(agent_result.final_verdict, gt.get("ground_truth_verdict", "ERROR"))

        meta = agent_result.metadata
        actual_model = meta.get("actual_model", model_name)

        record: Dict[str, Any] = {
            "run_id": run_id,
            "task": task_id,
            "condition": condition,
            "mode": mode,
            "agent_type": agent_type,
            "provider": provider.provider_name if mode == "real" else "simulation",
            "requested_model": model_name,
            "actual_model": actual_model,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seed": seed,
            "initial_workspace_sha256": initial_hash,
            "final_workspace_sha256": final_hash,
            "hidden_tests_in_workspace": hidden_in_ws,
            "apply_fix_in_workspace": oracle_in_ws,
            "max_turns_allocated": max_turns,
            "turns": agent_result.turns,
            "verdict": agent_result.final_verdict,
            "ground_truth_verdict": gt.get("ground_truth_verdict", "ERROR"),
            "outcome": outcome,
            "success": outcome.get("success", False),
            "false_pass": outcome.get("is_false_pass", False),
            "true_pass": outcome.get("is_true_pass", False),
            "false_fail": outcome.get("is_false_fail", False),
            "true_fail": outcome.get("is_true_fail", False),
            "stop_reason": agent_result.stop_reason,
            "tool_calls_count": len(agent_result.tool_calls),
            "tool_calls": [asdict(t) for t in agent_result.tool_calls],
            "token_usage": agent_result.token_usage.to_dict(),
            "input_tokens": agent_result.token_usage.input_tokens,
            "output_tokens": agent_result.token_usage.output_tokens,
            "cached_tokens": agent_result.token_usage.cached_tokens,
            "reasoning_tokens": agent_result.token_usage.reasoning_tokens,
            "total_tokens": agent_result.token_usage.total_tokens,
            "cost_usd": agent_result.cost_usd,
            "duration_seconds": agent_result.duration_seconds,
            "repaired": agent_result.repaired,
            "repair_rounds": agent_result.repair_rounds,
            "initial_flaw_detected": agent_result.initial_flaw_detected,
            "task_metadata": task_info,
            "metadata": meta,
            "ground_truth": gt,
        }
        return record

    finally:
        shutil.rmtree(temp_base, ignore_errors=True)


def compute_agent_condition_summary(records: List[Dict[str, Any]], condition: str) -> Dict[str, Any]:
    """Compute aggregated statistical summary for an agent condition."""
    n = len(records)
    if n == 0:
        return {}

    tp = sum(1 for r in records if r.get("true_pass"))
    fp = sum(1 for r in records if r.get("false_pass"))
    tn = sum(1 for r in records if r.get("true_fail"))
    fn = sum(1 for r in records if r.get("false_fail"))
    abstain = sum(1 for r in records if r.get("verdict") in ("ABSTAIN", "HUMAN_REVIEW_REQUIRED"))

    pass_claims = sum(1 for r in records if r.get("verdict") == "PASS")
    initial_detections = sum(1 for r in records if r.get("initial_flaw_detected"))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_accuracy = (recall + specificity) / 2.0
    reliability = (tp + tn) / n if n > 0 else 0.0

    false_pass_rate = fp / pass_claims if pass_claims > 0 else 0.0
    unconditional_false_pass_rate = fp / n if n > 0 else 0.0
    verified_correct_delivery_rate = tp / n if n > 0 else 0.0
    final_correct_implementation_rate = (tp + fn) / n if n > 0 else 0.0
    initial_detection_rejection_rate = initial_detections / n if n > 0 else 0.0

    total_in_tokens = sum(r.get("input_tokens", 0) for r in records)
    total_out_tokens = sum(r.get("output_tokens", 0) for r in records)
    total_cached_tokens = sum(r.get("cached_tokens", 0) for r in records)
    total_tokens = sum(r.get("total_tokens", 0) for r in records)
    total_cost = sum(r.get("cost_usd", 0.0) for r in records)
    total_duration = sum(r.get("duration_seconds", 0.0) for r in records)
    total_turns = sum(r.get("turns", 0) for r in records)

    return {
        "condition": condition,
        "sample_size": n,
        "signal_counts": {"TP": tp, "FP": fp, "TN": tn, "FN": fn, "ABSTAIN": abstain},
        "initial_detection_rejection_rate": initial_detection_rejection_rate,
        "false_pass_rate": false_pass_rate,
        "unconditional_false_pass_rate": unconditional_false_pass_rate,
        "verified_correct_delivery_rate": verified_correct_delivery_rate,
        "final_correct_implementation_rate": final_correct_implementation_rate,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
        "reliability": reliability,
        "mean_input_tokens": round(total_in_tokens / n, 1),
        "mean_output_tokens": round(total_out_tokens / n, 1),
        "mean_cached_tokens": round(total_cached_tokens / n, 1),
        "mean_total_tokens": round(total_tokens / n, 1),
        "total_tokens_all": total_tokens,
        "mean_cost_usd": round(total_cost / n, 6),
        "total_cost_usd": round(total_cost, 6),
        "mean_duration_seconds": round(total_duration / n, 3),
        "total_duration_seconds": round(total_duration, 3),
        "mean_turns": round(total_turns / n, 2),
    }


def run_agent_benchmark(
    tasks_dir: str = "benchmark/tasks",
    results_dir: Optional[str] = None,
    mode: str = "real",
    provider_name: Optional[str] = None,
    model_name: str = "claude-3-5-sonnet-20241022",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    seed: int = 42,
    runs: int = 1,
    max_turns: int = 15,
    preflight_only: bool = False,
    task_id: Optional[str] = None,
    condition: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute the Level 2 Coding-Agent Benchmark."""
    random.seed(seed)
    tasks_dir_abs = os.path.abspath(tasks_dir)

    # Determine results directory
    if not results_dir:
        if mode == "real":
            results_dir = "benchmark/results/agent"
        else:
            results_dir = "benchmark/results/agent_simulation"
    results_dir_abs = os.path.abspath(results_dir)

    for subdir in ["raw", "summaries", "metrics", "report"]:
        os.makedirs(os.path.join(results_dir_abs, subdir), exist_ok=True)

    print(f"\n{'='*75}")
    print(f"  LEVEL 2: CODING-AGENT A/B/C BENCHMARK")
    print(f"{'='*75}")
    print(f"Execution Mode  : {mode.upper()}")
    print(f"Tasks directory : {tasks_dir_abs}")
    print(f"Results         : {results_dir_abs}")
    print(f"Model Profile   : {model_name}")
    print(f"Max Turns/Trial : {max_turns}")
    print(f"Runs per trial  : {runs}")
    print(f"Random seed     : {seed}\n")

    # Instantiate Provider
    provider = get_provider(
        provider_name=provider_name,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    # ------------------------------------------------------------------ #
    # Phase 1: Preflight & Connectivity Validation
    # ------------------------------------------------------------------ #
    print(f"[Preflight] Initializing {provider.provider_name.upper()} provider...")
    if mode == "real":
        healthy, status_msg = provider.health_check()
        if not healthy:
            print(f"\n[FAIL CLOSED] Preflight Health Check Failed: {status_msg}", file=sys.stderr)
            print(
                "[ERROR] Level 2 requires live LLM communication. "
                "The benchmark will NEVER silently fall back to simulation.\n"
                "Please configure a valid API key (e.g. ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY) "
                "or specify an accessible local endpoint (e.g. --base-url http://localhost:11434/v1).",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[Preflight] Provider verified: {status_msg}")
    else:
        print("[Preflight] Running in SIMULATION mode (TestAgent fallback). Not valid for Level 2 publication.")

    if preflight_only:
        print("\n[Preflight] Preflight validation succeeded. Exiting (--preflight-only specified).")
        return {"status": "PREFLIGHT_PASSED"}

    # ------------------------------------------------------------------ #
    # Phase 2: Full Benchmark Execution (36 Trials)
    # ------------------------------------------------------------------ #
    if task_id:
        if not os.path.isdir(os.path.join(tasks_dir_abs, task_id)):
            print(f"[ERROR] Task directory not found: {os.path.join(tasks_dir_abs, task_id)}", file=sys.stderr)
            sys.exit(1)
        task_ids = [task_id]
    else:
        task_ids = sorted([
            d for d in os.listdir(tasks_dir_abs)
            if os.path.isdir(os.path.join(tasks_dir_abs, d))
        ])

    active_conditions = [condition] if condition else CONDITIONS
    trials: List[Tuple[str, str]] = []
    for _ in range(runs):
        for t_id in task_ids:
            for c in active_conditions:
                trials.append((t_id, c))

    random.shuffle(trials)
    print(f"\nTotal agent trials: {len(trials)} (shuffled across {len(task_ids)} tasks)\n")

    all_results: List[Dict[str, Any]] = []
    results_by_condition: Dict[str, List[Dict[str, Any]]] = {c: [] for c in CONDITIONS}

    ts_start = time.strftime("%Y%m%dT%H%M%S")
    raw_file = os.path.join(results_dir_abs, "raw", f"run_{ts_start}.jsonl")

    with open(raw_file, "w", encoding="utf-8") as raw_fh:
        for idx, (task_id, cond) in enumerate(trials, 1):
            run_id = f"agent_{ts_start}_{idx:04d}"
            label = f"Trial {idx:03d}/{len(trials):03d} | {task_id:28s} | {cond:14s}"
            print(label, end="", flush=True)

            record = run_single_agent_trial(
                task_id=task_id,
                condition=cond,
                tasks_dir=tasks_dir_abs,
                mode=mode,
                provider=provider,
                model_name=model_name,
                seed=seed,
                run_id=run_id,
                max_turns=max_turns,
            )

            v = record.get("verdict", "ERROR")
            gt_v = record.get("ground_truth_verdict", "ERROR")
            cls_name = record.get("outcome", {}).get("classification", "?")
            tok = record.get("total_tokens", 0)
            cost = record.get("cost_usd", 0.0)
            dur = record.get("duration_seconds", 0.0)

            print(f" -> {v:5s} | GT:{gt_v:4s} | {cls_name:12s} | {tok:5d} tok | ${cost:.4f} | {dur:.2f}s")

            all_results.append(record)
            results_by_condition[cond].append(record)

            raw_fh.write(json.dumps(record, default=str) + "\n")
            raw_fh.flush()

    # Summaries
    b_sum = compute_agent_condition_summary(results_by_condition["baseline"], "baseline")
    g_sum = compute_agent_condition_summary(results_by_condition["generic_review"], "generic_review")
    j_sum = compute_agent_condition_summary(results_by_condition["the_judge"], "the_judge")
    summaries = {"baseline": b_sum, "generic_review": g_sum, "the_judge": j_sum}

    for cond_name, sm in summaries.items():
        fp = os.path.join(results_dir_abs, "summaries", f"{cond_name}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(sm, f, indent=2)

    # Per-task matrix
    per_task: List[Dict[str, Any]] = []
    b_map = {r["task"]: r for r in results_by_condition["baseline"]}
    g_map = {r["task"]: r for r in results_by_condition["generic_review"]}
    j_map = {r["task"]: r for r in results_by_condition["the_judge"]}

    for tid in task_ids:
        br = b_map.get(tid, {})
        gr = g_map.get(tid, {})
        jr = j_map.get(tid, {})
        meta = TASK_BY_ID.get(tid, {})

        bo = br.get("outcome", {}).get("classification", "ERROR")
        go = gr.get("outcome", {}).get("classification", "ERROR")
        jo = jr.get("outcome", {}).get("classification", "ERROR")

        if jo == "TRUE_PASS" and bo != "TRUE_PASS":
            contrib = "IMPROVEMENT"
        elif jo == "FALSE_FAIL" and bo == "TRUE_PASS":
            contrib = "REGRESSION"
        elif jo == "FALSE_FAIL":
            contrib = "DETECT_UNVERIFIED"
        elif jo == "FALSE_PASS" and bo == "FALSE_PASS":
            contrib = "ALL_FALSE_PASS"
        else:
            contrib = "NEUTRAL"

        per_task.append({
            "task_id": tid,
            "difficulty": meta.get("difficulty", "medium"),
            "defect_nature": meta.get("defect_nature", "TESTED_DEFECT"),
            "ground_truth_verdict": jr.get("ground_truth_verdict", "?"),
            "baseline_outcome": bo,
            "generic_review_outcome": go,
            "judge_outcome": jo,
            "judge_contribution": contrib,
            "judge_tokens": jr.get("total_tokens", 0),
            "judge_cost_usd": jr.get("cost_usd", 0.0),
        })

    with open(os.path.join(results_dir_abs, "metrics", "per_task.json"), "w", encoding="utf-8") as f:
        json.dump(per_task, f, indent=2)

    # Quality vs Cost
    b_fp = b_sum.get("false_pass_rate", 1.0)
    j_fp = j_sum.get("false_pass_rate", 1.0)
    fp_red = ((b_fp - j_fp) / b_fp * 100.0) if b_fp > 0 else 0.0

    b_tok = b_sum.get("mean_total_tokens", 1)
    j_tok = j_sum.get("mean_total_tokens", 1)
    tok_ratio = j_tok / b_tok if b_tok > 0 else 1.0

    quality_vs_cost = {
        "false_pass_reduction_pct": round(fp_red, 1),
        "verified_delivery_delta": round(j_sum.get("verified_correct_delivery_rate", 0.0) - b_sum.get("verified_correct_delivery_rate", 0.0), 3),
        "token_overhead_ratio": round(tok_ratio, 2),
        "cost_delta_usd": round(j_sum.get("mean_cost_usd", 0.0) - b_sum.get("mean_cost_usd", 0.0), 4),
    }

    with open(os.path.join(results_dir_abs, "metrics", "quality_vs_cost.json"), "w", encoding="utf-8") as f:
        json.dump(quality_vs_cost, f, indent=2)

    # Generate 25-Section Report
    run_meta = {
        "task_count": len(task_ids),
        "runs_per_trial": runs,
        "model": model_name,
        "provider": provider.provider_name if mode == "real" else "simulation",
        "mode": mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    report_md = generate_agent_report(summaries, per_task, quality_vs_cost, run_meta)

    report_path = os.path.join(results_dir_abs, "report", "agent_benchmark_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    if mode == "real":
        main_report_path = os.path.abspath(os.path.join(_PROJECT_ROOT, "benchmark", "THE_JUDGE_AGENT_BENCHMARK_REPORT.md"))
        with open(main_report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
    else:
        main_report_path = os.path.abspath(os.path.join(results_dir_abs, "SIMULATED_BENCHMARK_REPORT.md"))
        with open(main_report_path, "w", encoding="utf-8") as f:
            f.write(report_md)

    # Scorecard
    print(f"\n{'='*80}")
    print(f"  LEVEL 2 BENCHMARK SCORECARD  (Mode: {mode.upper()} | Model: {model_name})")
    print(f"{'='*80}")
    print(f"{'Metric':<40} {'Baseline (A)':>12} {'Generic (B)':>12} {'The Judge (C)':>14}")
    print("-" * 80)
    for label, key in [
        ("Initial defect detection rate", "initial_detection_rejection_rate"),
        ("False PASS rate (FP / PASS claims)", "false_pass_rate"),
        ("Unconditional False PASS (FP / total)", "unconditional_false_pass_rate"),
        ("Verified correct delivery (TP / total)", "verified_correct_delivery_rate"),
        ("Balanced accuracy", "balanced_accuracy"),
        ("Reliability ((TP+TN)/total)", "reliability"),
    ]:
        print(f"{label:<40} {b_sum.get(key, 0.0)*100:>11.1f}% {g_sum.get(key, 0.0)*100:>11.1f}% {j_sum.get(key, 0.0)*100:>13.1f}%")

    print("-" * 80)
    print(f"{'Mean Total Tokens':<40} {b_sum.get('mean_total_tokens', 0):>12,.0f} {g_sum.get('mean_total_tokens', 0):>12,.0f} {j_sum.get('mean_total_tokens', 0):>14,.0f}")
    print(f"{'Mean Cost per Task (USD)':<40} ${b_sum.get('mean_cost_usd', 0.0):>11.4f} ${g_sum.get('mean_cost_usd', 0.0):>11.4f} ${j_sum.get('mean_cost_usd', 0.0):>13.4f}")
    print(f"{'Mean Duration (seconds)':<40} {b_sum.get('mean_duration_seconds', 0.0):>11.2f}s {g_sum.get('mean_duration_seconds', 0.0):>11.2f}s {j_sum.get('mean_duration_seconds', 0.0):>13.2f}s")
    print("=" * 80)
    print(f"Report written to: {main_report_path}\n")

    return {
        "summaries": summaries,
        "per_task": per_task,
        "quality_vs_cost": quality_vs_cost,
        "report_path": main_report_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Level 2 Coding-Agent Benchmark Runner")
    parser.add_argument("--mode", choices=["real", "simulated"], default="real", help="Execution mode (default: real)")
    parser.add_argument("--provider", choices=["anthropic", "openai", "gemini", "ollama"], help="LLM provider adapter")
    parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Model profile identifier")
    parser.add_argument("--api-key", help="API authentication key (defaults to environment)")
    parser.add_argument("--base-url", help="Base URL for provider endpoint (for local or custom servers)")
    parser.add_argument("--tasks", default="benchmark/tasks", help="Tasks directory")
    parser.add_argument("--results", help="Output results directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--runs", type=int, default=1, help="Runs per trial")
    parser.add_argument("--max-turns", type=int, default=15, help="Equalized max turn budget across A/B/C")
    parser.add_argument("--task", help="Run only a specific task ID (e.g. 01_auth_jwt)")
    parser.add_argument("--condition", choices=CONDITIONS, help="Run only a specific condition (e.g. baseline)")
    parser.add_argument("--preflight-only", action="store_true", help="Run only preflight connectivity validation")
    args = parser.parse_args()

    run_agent_benchmark(
        tasks_dir=args.tasks,
        results_dir=args.results,
        mode=args.mode,
        provider_name=args.provider,
        model_name=args.model,
        api_key=args.api_key,
        base_url=args.base_url,
        seed=args.seed,
        runs=args.runs,
        max_turns=args.max_turns,
        preflight_only=args.preflight_only,
        task_id=args.task,
        condition=args.condition,
    )


if __name__ == "__main__":
    main()
