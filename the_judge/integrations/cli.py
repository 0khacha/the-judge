import argparse
import json
import os
import sys
from typing import Any, Dict

from the_judge.api import verify
from the_judge.integrations.demo import run_demo


def main(args_list=None) -> int:
    """Main CLI entrypoint for The Judge v1.0.0."""
    parser = argparse.ArgumentParser(
        prog="judge",
        description="The Judge v1.0.0 — Independent Verification Layer for AI-Generated Software",
    )
    parser.add_argument("--version", action="version", version="The Judge v1.0.0")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify workspace code")
    verify_parser.add_argument("workspace", nargs="?", default=".", help="Path to workspace directory or python file")
    verify_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON matching result.schema.json")
    verify_parser.add_argument("--task-spec", type=str, default=None, help="Path to specification file (JSON or YAML)")

    # contract command
    contract_parser = subparsers.add_parser("contract", help="Inspect requirement specification contract")
    contract_parser.add_argument("workspace", nargs="?", default=".", help="Path to workspace directory or python file")
    contract_parser.add_argument("--json", action="store_true", help="Output specification contract in JSON format")
    contract_parser.add_argument("--task-spec", type=str, default=None, help="Path to specification file (JSON or YAML)")

    # demo command
    subparsers.add_parser("demo", help="Run 60-second interactive verification demo")

    # hook command
    hook_parser = subparsers.add_parser("hook", help="Manage git verification hooks")
    hook_sub = hook_parser.add_subparsers(dest="hook_action", help="Hook actions")
    hook_install = hook_sub.add_parser("install", help="Install a git hook")
    hook_install.add_argument("--pre-push", action="store_true", help="Install pre-push hook instead of pre-commit")
    hook_install.add_argument("workspace", nargs="?", default=".", help="Path to workspace")
    hook_uninstall = hook_sub.add_parser("uninstall", help="Uninstall a git hook")
    hook_uninstall.add_argument("--pre-push", action="store_true", help="Uninstall pre-push hook instead of pre-commit")
    hook_uninstall.add_argument("workspace", nargs="?", default=".", help="Path to workspace")

    # init command
    init_parser = subparsers.add_parser("init", help="Generate IDE integration files")
    init_parser.add_argument("target", choices=["vscode"], help="Target IDE")
    init_parser.add_argument("workspace", nargs="?", default=".", help="Path to workspace")

    # improve command
    improve_parser = subparsers.add_parser("improve", help="Run multi-round iterative improvement loop")
    improve_parser.add_argument("workspace", nargs="?", default=".", help="Path to workspace directory or file")
    improve_parser.add_argument("--max-rounds", type=int, default=5, help="Maximum improvement rounds (default: 5)")
    improve_parser.add_argument("--target-score", type=float, default=90.0, help="Target quality score threshold (default: 90.0)")
    improve_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON history")

    args = parser.parse_args(args_list)

    if args.command == "demo":
        run_demo()
        return 0

    if args.command == "hook":
        return _run_hook_command(args)

    if args.command == "init":
        return _run_init_command(args)

    if args.command == "watch":
        return _run_watch_command(args)

    if args.command == "improve":
        return _run_improve_command(args)

    workspace_path = getattr(args, "workspace", ".")
    is_json = getattr(args, "json", False)
    task_spec_path = getattr(args, "task_spec", None)

    # Auto-discover conventional task contract files if not specified
    if not task_spec_path and os.path.isdir(workspace_path):
        for candidate in ("judge.json", "judge.yaml", "task_spec.json"):
            cp = os.path.join(workspace_path, candidate)
            if os.path.exists(cp):
                task_spec_path = cp
                break

    if args.command == "contract":
        _run_contract_command(workspace_path, is_json, task_spec_path)
        return 0

    task_spec_dict = None
    if task_spec_path and os.path.exists(task_spec_path):
        try:
            with open(task_spec_path, "r", encoding="utf-8") as f:
                if task_spec_path.endswith((".yaml", ".yml")):
                    # Simple inline YAML parser fallback if PyYAML not installed
                    try:
                        import yaml
                        task_spec_dict = yaml.safe_load(f)
                    except ImportError:
                        task_spec_dict = json.load(f)
                else:
                    task_spec_dict = json.load(f)
        except Exception:
            task_spec_dict = None

    old_argv = list(sys.argv)
    try:
        sys.argv = [sys.argv[0]]
        verif_result = verify(workspace=workspace_path, task_spec=task_spec_dict)
    except Exception as e:
        if is_json:
            print(json.dumps({"error": str(e), "decision": "ERROR"}, indent=2))
        else:
            print(f"[EXECUTION ERROR] {e}")
        return 3
    finally:
        sys.argv = old_argv

    if is_json:
        print(json.dumps(verif_result.to_dict(), indent=2))
    else:
        _print_human_readable_result(workspace_path, verif_result)

    return 0 if verif_result.decision == "PASS" else (1 if verif_result.decision == "FAIL" else 2)


def _run_hook_command(args) -> int:
    """Handle the 'judge hook' subcommand."""
    from the_judge.integrations.hooks import install_hook, uninstall_hook

    hook_type = "pre-push" if getattr(args, "pre_push", False) else "pre-commit"
    workspace = getattr(args, "workspace", ".")

    if args.hook_action == "install":
        try:
            path = install_hook(workspace, hook_type)
            print(f"Installed {hook_type} hook at {path}")
            return 0
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except FileExistsError as e:
            print(f"Error: {e}")
            return 1

    elif args.hook_action == "uninstall":
        path = uninstall_hook(workspace, hook_type)
        if path:
            print(f"Removed {hook_type} hook from {path}")
        else:
            print(f"No Judge-installed {hook_type} hook found.")
        return 0

    else:
        print("Usage: judge hook {install|uninstall} [--pre-push] [workspace]")
        return 1


def _run_init_command(args) -> int:
    """Handle the 'judge init' subcommand."""
    workspace = getattr(args, "workspace", ".")

    if args.target == "vscode":
        from the_judge.integrations.ide import generate_vscode_tasks
        try:
            path = generate_vscode_tasks(workspace)
            print(f"Generated VS Code tasks at {path}")
            print("Open Command Palette (Ctrl+Shift+P) -> 'Tasks: Run Task' -> 'Judge: Verify Workspace'")
            return 0
        except FileExistsError as e:
            print(f"Error: {e}")
            return 1

    return 1


def _run_watch_command(args) -> int:
    """Handle the 'judge watch' subcommand."""
    from the_judge.integrations.watcher import watch_workspace

    workspace = getattr(args, "workspace", ".")
    debounce = getattr(args, "debounce", 2.0)

    try:
        watch_workspace(workspace, debounce_seconds=debounce)
    except KeyboardInterrupt:
        pass

    return 0


def _run_improve_command(args) -> int:
    """Handle the 'judge improve' subcommand for adaptive iterative refinement."""
    from the_judge.api import improve
    from the_judge.core.visual_engine import VisualEngine

    workspace = getattr(args, "workspace", ".")
    max_rounds = getattr(args, "max_rounds", 5)
    target_score = getattr(args, "target_score", 90.0)
    is_json = getattr(args, "json", False)

    ve = VisualEngine(workspace)
    is_visual, target_file = ve.is_visual_workspace()

    if not is_json:
        print("=" * 68)
        print("THE JUDGE — Adaptive Iterative Improvement Engine")
        if is_visual:
            print("Loop: Build -> Run -> Screenshot -> Evaluate -> Improve -> Compare -> Repeat")
            print(f"Classification   : [VISUAL PROJECT] (Target: {os.path.basename(target_file)})")
        else:
            print("Loop: Build -> Test -> Evaluate -> Identify Weaknesses -> Improve -> Re-test -> Repeat")
            print("Classification   : [NON-VISUAL PROJECT] (Code / Unit Tests / Behavioral Metrics)")
        print("=" * 68)
        print(f"Target Workspace : {os.path.abspath(workspace)}")
        print(f"Max Rounds       : {max_rounds}")
        print(f"Quality Target   : {target_score} / 100.0")
        print()

    old_argv = list(sys.argv)
    try:
        sys.argv = [sys.argv[0]]
        result = improve(workspace=workspace, max_rounds=max_rounds, target_score=target_score)
    except Exception as e:
        if is_json:
            print(json.dumps({"error": str(e), "outcome": "ERROR"}, indent=2))
        else:
            print(f"[IMPROVEMENT ENGINE ERROR] {e}")
        return 3
    finally:
        sys.argv = old_argv

    if is_json:
        print(json.dumps(result, indent=2))
        return 0

    history = result.get("history", [])
    screenshots_collected = []

    for round_item in history:
        round_num = round_item.get("round_number", 1)
        dec = round_item.get("decision", "UNKNOWN")
        score = round_item.get("numeric_score", 0.0)
        quality = round_item.get("quality", {})
        weaknesses = quality.get("weaknesses", [])
        repair = round_item.get("repair", {})
        screenshot = round_item.get("screenshot")

        if screenshot:
            screenshots_collected.append(screenshot)

        print(f"[Round {round_num}/{result.get('total_rounds', max_rounds)}] Evaluation & Refinement")
        print(f"  Decision       : {dec}")
        print(f"  Quality Score  : {score} / 100.0")
        print(f"  Weaknesses     : {len(weaknesses)} issue(s) identified")

        if screenshot:
            rel_snap = os.path.relpath(screenshot, os.path.abspath(workspace)) if os.path.isabs(screenshot) else screenshot
            print(f"  Visual Evidence: {rel_snap}")

        if repair and repair.get("summary"):
            print(f"  Action Taken   : {repair.get('summary')}")
        print()

    outcome = result.get("outcome", "COMPLETED")
    if outcome in ("PASS", "QUALITY_TARGET_MET"):
        initial_score = history[0].get("numeric_score", 0.0) if history else 0.0
        final_score = result.get("quality", {}).get("score", 0.0)
        diff = round(final_score - initial_score, 1)
        diff_str = f"+{diff}" if diff >= 0 else str(diff)
        print("=" * 68)
        print(f"SUCCESS: Quality target achieved in {result.get('total_rounds')} round(s)!")
        print(f"Score Progression : {initial_score} -> {final_score} ({diff_str} points)")
        if is_visual and screenshots_collected:
            prog_str = " -> ".join([f"Round {i+1}" for i in range(len(screenshots_collected))])
            print(f"Visual Progression: {prog_str} preserved in _judge_visual/")
        print("=" * 68)
        return 0
    else:
        print("=" * 68)
        print(f"OUTCOME: {outcome}")
        if result.get("reason"):
            print(f"Reason: {result.get('reason')}")
        print("=" * 68)
        return 1


def _run_contract_command(workspace_path: str, is_json: bool, task_spec_path: str = None) -> None:
    task_spec_dict = None
    if task_spec_path and os.path.exists(task_spec_path):
        with open(task_spec_path, "r", encoding="utf-8") as f:
            task_spec_dict = json.load(f)

    verif_result = verify(workspace=workspace_path, task_spec=task_spec_dict)
    spec_cov = verif_result.trust_profile.get("specification_coverage", {})

    if is_json:
        print(json.dumps(spec_cov, indent=2))
    else:
        print("=" * 68)
        print("THE JUDGE v1.0.0 — Requirement Specification Contract Report")
        print("=" * 68)
        print(f"Workspace: {os.path.abspath(workspace_path)}")
        print()

        summary = spec_cov.get("summary", {})
        print("SPECIFICATION COVERAGE SUMMARY")
        print("------------------------------")
        print(f"Total Requirements Identified : {summary.get('total_requirements', 0)}")
        print(f"Requirements Verified         : {summary.get('verified_count', 0)}")
        print(f"Partially Verified            : {summary.get('partially_verified_count', 0)}")
        print(f"Unverified                    : {summary.get('unverified_count', 0)}")
        print(f"Conflicting / Failed          : {summary.get('conflicting_count', 0)}")
        print(f"Critical Requirement Coverage : {summary.get('critical_coverage_pct', 0.0)}%")
        print(f"Overall Requirement Coverage  : {summary.get('overall_coverage_pct', 0.0)}%")
        print(f"Specification Escape Rate     : {summary.get('specification_escape_rate_pct', 0.0)}%")
        print()

        print("REQUIREMENT DETAILS")
        print("-------------------")
        for req in spec_cov.get("requirements", []):
            st = req.get("status", "UNVERIFIED")
            symbol = "OK" if st == "VERIFIED" else ("PARTIAL" if st == "PARTIALLY_VERIFIED" else "FAIL")
            print(f"[{symbol}] [{st}] {req.get('id')}: {req.get('description')}")
            print(f"    Category: {req.get('category')} | Priority: {req.get('priority')}")
            if req.get("unverified_reason"):
                print(f"    Reason:   {req.get('unverified_reason')}")
            for p in req.get("mapped_properties", []):
                print(f"    |-- Property: {p.get('property_name')} (Provenance: {p.get('provenance')}, Confidence: {p.get('confidence')})")
            print()
        print("=" * 68)


def _print_human_readable_result(workspace_path: str, result: Any) -> None:
    print("=" * 68)
    print("THE JUDGE v1.0.0 — Verification Report")
    print("=" * 68)
    print(f"Workspace: {os.path.abspath(workspace_path)}")
    print()

    tp = result.trust_profile
    ev_level = tp.get("evidence_level", 0)

    env_ok = tp.get("environment_isolation_subdimensions", {}).get("process_isolation") == "VERIFIED"
    chal_ok = tp.get("evidence_integrity_subdimensions", {}).get("challenge_integrity") == "VERIFIED"
    beh_ok = result.decision != "FAIL" and ev_level >= 2
    indep_ok = tp.get("evidence_integrity_subdimensions", {}).get("evidence_independence") in ("VERIFIED", "PARTIAL")
    adv_ok = tp.get("adversarial_robustness_subdimensions", {}).get("evasion_resistance") == "VERIFIED"

    print(f"[1/5] Environment isolation       {'PASS' if env_ok else 'FAIL'}")
    print(f"[2/5] Challenge integrity         {'PASS' if chal_ok else 'FAIL'}")
    print(f"[3/5] Behavioral verification    {'PASS' if beh_ok else ('ABSTAIN' if result.decision == 'ABSTAIN' else 'FAIL')}")
    print(f"[4/5] Evidence independence      {'PASS' if indep_ok else 'FAIL'}")
    print(f"[5/5] Adversarial checks          {'PASS' if adv_ok else 'FAIL'}")
    print()

    spec_cov = tp.get("specification_coverage", {}).get("summary", {})
    if spec_cov:
        print("SPECIFICATION COVERAGE")
        print("----------------------")
        print(f"Critical Coverage : {spec_cov.get('critical_coverage_pct', 0.0)}%")
        print(f"Overall Coverage  : {spec_cov.get('overall_coverage_pct', 0.0)}%")
        print(f"Verified / Total  : {spec_cov.get('verified_count', 0)} / {spec_cov.get('total_requirements', 0)}")
        print()

    print(f"DECISION: {result.decision}")
    print(f"Numeric Trust Score: {result.numeric_score} / 100.0")
    print()

    if result.decision == "FAIL":
        print("FINDINGS:")
        for idx, f in enumerate(result.findings, 1):
            print(f"  [{idx}] [{f.severity.upper()}] {f.description}")
            if f.observed:
                print(f"      Observed: {f.observed}")
            if f.expected:
                print(f"      Expected: {f.expected}")
            if f.suggested_focus:
                print(f"      Focus:    {f.suggested_focus}")
            print()

    elif result.decision == "ABSTAIN":
        print("REASON FOR ABSTAIN:")
        for note in result.insufficient_notes:
            print(f"  - {note}")
        print("\nThe Judge refuses to grant PASS when critical requirements remain unverified.")
        print()

    print("=" * 68)


if __name__ == "__main__":
    main()
