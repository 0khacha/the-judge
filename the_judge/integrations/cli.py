import argparse
import contextlib
import json
import os
import sys
from typing import Any, Optional

from the_judge.api import verify
from the_judge.integrations.demo import run_demo


def main(args_list=None) -> int:
    """Main CLI entrypoint for The Judge v1.0.0."""
    parser = argparse.ArgumentParser(
        prog="judge",
        description="The Judge v1.0.0 -- Adversarial Verification & Improvement Engine",
    )
    parser.add_argument("--version", action="version", version="The Judge v1.0.0")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify workspace code")
    verify_parser.add_argument(
        "workspace", nargs="?", default=".", help="Path to workspace directory or python file"
    )
    verify_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON matching result.schema.json",
    )
    verify_parser.add_argument(
        "--task-spec", type=str, default=None, help="Path to specification file (JSON or YAML)"
    )

    # contract command
    contract_parser = subparsers.add_parser(
        "contract", help="Inspect requirement specification contract"
    )
    contract_parser.add_argument(
        "workspace", nargs="?", default=".", help="Path to workspace directory or python file"
    )
    contract_parser.add_argument(
        "--json", action="store_true", help="Output specification contract in JSON format"
    )
    contract_parser.add_argument(
        "--task-spec", type=str, default=None, help="Path to specification file (JSON or YAML)"
    )

    # demo command
    subparsers.add_parser("demo", help="Run 60-second interactive verification demo")

    # hook command
    hook_parser = subparsers.add_parser("hook", help="Manage git verification hooks")
    hook_sub = hook_parser.add_subparsers(dest="hook_action", help="Hook actions")
    hook_install = hook_sub.add_parser("install", help="Install a git hook")
    hook_install.add_argument(
        "--pre-push", action="store_true", help="Install pre-push hook instead of pre-commit"
    )
    hook_install.add_argument("workspace", nargs="?", default=".", help="Path to workspace")
    hook_uninstall = hook_sub.add_parser("uninstall", help="Uninstall a git hook")
    hook_uninstall.add_argument(
        "--pre-push", action="store_true", help="Uninstall pre-push hook instead of pre-commit"
    )
    hook_uninstall.add_argument("workspace", nargs="?", default=".", help="Path to workspace")

    # init command
    init_parser = subparsers.add_parser("init", help="Generate IDE integration files")
    init_parser.add_argument("target", choices=["vscode"], help="Target IDE")
    init_parser.add_argument("workspace", nargs="?", default=".", help="Path to workspace")

    # improve command
    improve_parser = subparsers.add_parser(
        "improve",
        help="Run multi-round adversarial improvement loop (Build->Evidence->Critique->Improve->Repeat)",
    )
    improve_parser.add_argument(
        "workspace", nargs="?", default=".", help="Path to workspace directory or file"
    )
    improve_parser.add_argument(
        "--max-rounds", type=int, default=5, help="Maximum improvement rounds (default: 5)"
    )
    improve_parser.add_argument(
        "--target-score",
        type=float,
        default=90.0,
        help="Target quality score threshold (default: 90.0)",
    )
    improve_parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON history"
    )
    improve_parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating the HTML progress report",
    )

    # critique command
    critique_parser = subparsers.add_parser(
        "critique",
        help="Run independent adversarial critique -- classify findings by evidence level",
    )
    critique_parser.add_argument(
        "workspace", nargs="?", default=".", help="Path to workspace directory or file"
    )
    critique_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    critique_parser.add_argument(
        "--task-spec", type=str, default=None, help="Path to specification file"
    )

    # watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch workspace and re-verify on every .py file save",
    )
    watch_parser.add_argument(
        "workspace", nargs="?", default=".", help="Path to workspace directory"
    )
    watch_parser.add_argument(
        "--debounce",
        type=float,
        default=2.0,
        help="Debounce delay in seconds between re-verifications (default: 2.0)",
    )

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

    if args.command == "critique":
        return _run_critique_command(args)

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
            with open(task_spec_path, encoding="utf-8") as f:
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
        removed: Optional[str] = uninstall_hook(workspace, hook_type)
        if removed:
            print(f"Removed {hook_type} hook from {removed}")
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
            print(
                "Open Command Palette (Ctrl+Shift+P) -> 'Tasks: Run Task' -> 'Judge: Verify Workspace'"
            )
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

    with contextlib.suppress(KeyboardInterrupt):
        watch_workspace(workspace, debounce_seconds=debounce)

    return 0


def _run_improve_command(args) -> int:
    """Handle the 'judge improve' subcommand -- adversarial improvement loop."""
    from the_judge.api import improve
    from the_judge.core.visual_engine import VisualEngine
    from the_judge.integrations.audit_trail import AuditTrail
    from the_judge.integrations.progress_report import generate_progress_report

    workspace = getattr(args, "workspace", ".")
    max_rounds = getattr(args, "max_rounds", 5)
    target_score = getattr(args, "target_score", 90.0)
    is_json = getattr(args, "json", False)
    no_report = getattr(args, "no_report", False)

    ve = VisualEngine(workspace)
    is_visual, target_file = ve.is_visual_workspace()

    if not is_json:
        print("=" * 70)
        print("THE JUDGE -- Adversarial Improvement Engine")
        print("Loop: WORK -> EVIDENCE -> CRITIQUE -> IDENTIFY WEAKNESSES -> IMPROVE -> REPEAT")
        print("=" * 70)
        domain_label = "[VISUAL]" if is_visual else "[NON-VISUAL]"
        if is_visual:
            print(f"Classification   : {domain_label} -- screenshots captured as visual evidence")
        else:
            print(f"Classification   : {domain_label} -- tests, static analysis, behavioral checks")
        print(f"Target Workspace : {os.path.abspath(workspace)}")
        print(f"Max Rounds       : {max_rounds}")
        print(f"Quality Target   : {target_score} / 100.0")
        print("Stop Requires    : score≥threshold AND no blockers AND sufficient evidence")
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
    total = result.get("total_rounds", max_rounds)

    for round_item in history:
        round_num = round_item.get("round_number", 1)
        dec = round_item.get("decision", "UNKNOWN")
        score = round_item.get("numeric_score", 0.0)
        round_item.get("quality", {})
        repair = round_item.get("repair", {})
        screenshot = round_item.get("screenshot")
        critique = round_item.get("critique", {})
        ev_suf = (
            critique.get("evidence_sufficiency", {}).get("level", "unknown")
            if isinstance(critique.get("evidence_sufficiency"), dict)
            else critique.get("evidence_sufficiency", "unknown")
        )
        has_blockers = critique.get("has_blockers", False)
        skeptic = critique.get("skeptic_summary", "")
        contradictions = critique.get("contradictions", [])
        findings = critique.get("findings", [])

        if screenshot:
            screenshots_collected.append(screenshot)

        print(f"[Round {round_num}/{total}] Critique & Refinement")
        print(f"  Decision       : {dec}")
        print(f"  Quality Score  : {score:.1f} / 100.0")
        print(
            f"  Evidence       : {ev_suf.upper()}{'  ⚠ BLOCKERS PRESENT' if has_blockers else ''}"
        )

        if skeptic:
            print(f"  Critique       : {skeptic[:120]}{'...' if len(skeptic) > 120 else ''}")

        if contradictions:
            print(f"  Contradictions : {len(contradictions)} detected")
            for c in contradictions[:2]:
                print(f"    ↳ {c.get('description', '')[:100]}")

        # Show top evidence-classified findings
        top_findings = [
            f
            for f in findings
            if f.get("is_blocker") or f.get("evidence_level") in ("evidence_backed", "contradicted")
        ][:3]
        if top_findings:
            print("  Key Findings   :")
            for f in top_findings:
                ev = f.get("evidence_level", "").upper().replace("_", " ")
                sev = f.get("severity", "").upper()
                desc = f.get("description", "")[:90]
                blocker = " [BLOCKER]" if f.get("is_blocker") else ""
                print(f"    [{ev}][{sev}]{blocker} {desc}")

        if screenshot:
            rel = (
                os.path.relpath(screenshot, os.path.abspath(workspace))
                if os.path.isabs(screenshot)
                else screenshot
            )
            print(f"  Screenshot     : {rel}")

        if repair and repair.get("summary"):
            print(f"  Action Taken   : {repair.get('summary')[:120]}")
        print()

    outcome = result.get("outcome", "COMPLETED")

    # Generate progress report
    report_path = None
    if not no_report:
        try:
            audit_data = result.get("audit_trail", {})
            # Reconstruct a lightweight AuditTrail for the report
            from the_judge.integrations.audit_trail import RoundRecord

            trail = AuditTrail()
            for r in audit_data.get("rounds", []):
                rec = RoundRecord(
                    round_number=r.get("round_number", 0),
                    timestamp=r.get("timestamp", ""),
                    workspace_hash=r.get("workspace_hash", ""),
                    domain=r.get("domain", ""),
                    previous_score=r.get("scores", {}).get("previous", 0.0),
                    new_score=r.get("scores", {}).get("new", 0.0),
                    decision=r.get("verification", {}).get("decision", ""),
                    critique_findings=r.get("critique", {}).get("findings", []),
                    contradictions=r.get("critique", {}).get("contradictions", []),
                    skeptic_summary=r.get("critique", {}).get("skeptic_summary", ""),
                    has_blockers=r.get("critique", {}).get("has_blockers", False),
                    evidence_sufficiency=r.get("critique", {}).get(
                        "evidence_sufficiency", "unknown"
                    ),
                    improvement_actions=r.get("changes", {}).get("improvement_actions", []),
                    resolved_finding_ids=r.get("resolution", {}).get("resolved_finding_ids", []),
                    remaining_findings=r.get("resolution", {}).get("remaining_findings", []),
                    screenshot_path=r.get("visual", {}).get("screenshot_path"),
                    loop_decision=r.get("loop", {}).get("decision", "continue"),
                    stop_reason=r.get("loop", {}).get("stop_reason"),
                )
                trail.record_round(rec)

            report_dir = (
                os.path.join(os.path.abspath(workspace), "_judge_visual")
                if is_visual
                else os.path.join(os.path.abspath(workspace), "_judge_report")
            )
            report_path = generate_progress_report(
                audit_trail=trail,
                workspace=workspace,
                outcome=outcome,
                output_dir=report_dir,
                is_visual=is_visual,
            )
            # Also save audit trail JSON
            trail.save_to_disk(report_dir)
        except Exception:
            pass

    print("=" * 70)
    if outcome == "PASS":
        initial_score = history[0].get("numeric_score", 0.0) if history else 0.0
        final_score = result.get("quality", {}).get("score", 0.0)
        diff = round(final_score - initial_score, 1)
        diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
        print(f"SUCCESS: All stop conditions met in {result.get('total_rounds')} round(s).")
        print(f"Score Progression : {initial_score:.1f} -> {final_score:.1f} ({diff_str} points)")
        print("Evidence          : sufficient, no blockers, no contradictions")
        if is_visual and screenshots_collected:
            print(
                f"Visual Evidence   : {len(screenshots_collected)} screenshot(s) in _judge_visual/"
            )
        if report_path:
            rel_rep = os.path.relpath(report_path, os.path.abspath(workspace))
            print(f"Progress Report   : {rel_rep}")
        print("=" * 70)
        return 0
    else:
        print(f"OUTCOME: {outcome}")
        if result.get("reason"):
            print(f"Reason  : {result.get('reason')}")
        # Show remaining blockers if any
        last = history[-1] if history else {}
        last_critique = last.get("critique", {})
        remaining = last_critique.get("findings", []) if isinstance(last_critique, dict) else []
        blockers = [f for f in remaining if f.get("is_blocker")]
        if blockers:
            print(f"Blockers: {len(blockers)} unresolved")
            for b in blockers[:3]:
                ev = b.get("evidence_level", "").upper().replace("_", " ")
                sev = b.get("severity", "").upper()
                print(f"  [{ev}][{sev}] {b.get('description', '')[:100]}")
        if report_path:
            rel_rep = os.path.relpath(report_path, os.path.abspath(workspace))
            print(f"Progress Report : {rel_rep}")
        print("=" * 70)
        return 1


def _run_critique_command(args) -> int:
    """Handle the 'judge critique' subcommand -- independent adversarial critique."""
    from the_judge.api import critique, verify
    from the_judge.core.evidence import capture_evidence

    workspace = getattr(args, "workspace", ".")
    is_json = getattr(args, "json", False)
    task_spec_path = getattr(args, "task_spec", None)

    task_spec_dict = None
    if task_spec_path and os.path.exists(task_spec_path):
        try:
            with open(task_spec_path, encoding="utf-8") as f:
                task_spec_dict = json.load(f)
        except Exception:
            pass

    old_argv = list(sys.argv)
    try:
        sys.argv = [sys.argv[0]]
        capture_evidence(os.path.abspath(workspace), task_spec=task_spec_dict)
        verify(workspace=workspace, task_spec=task_spec_dict)
        critique_result = critique(workspace=workspace, task_spec=task_spec_dict)
    except Exception as e:
        if is_json:
            print(json.dumps({"error": str(e), "outcome": "ERROR"}, indent=2))
        else:
            print(f"[CRITIQUE ERROR] {e}")
        return 3
    finally:
        sys.argv = old_argv

    if is_json:
        print(json.dumps(critique_result.to_dict(), indent=2))
        return 0

    _print_critique_result(workspace, critique_result)
    return 0 if not critique_result.has_blockers() else 1


def _print_critique_result(workspace_path: str, result: Any) -> None:
    """Print a human-readable adversarial critique report."""
    sep = "=" * 70
    print(sep)
    print("THE JUDGE -- Independent Adversarial Critique")
    print(sep)
    print(f"Workspace  : {os.path.abspath(workspace_path)}")
    print(f"Domain     : {result.domain.replace('_', ' ').title()}")
    print()

    # Evidence sufficiency
    es = result.evidence_sufficiency
    suf_label = es.level.upper()
    print("EVIDENCE SUFFICIENCY")
    print("-" * 40)
    print(f"  Status        : {suf_label}")
    print(f"  Independent   : {es.independent_tests} test(s)")
    print(f"  Agent-Authored: {es.agent_controlled_tests} test(s)")
    print(f"  Contradictions: {'YES' if es.has_contradictions else 'none'}")
    if es.reasons:
        for r in es.reasons:
            print(f"  Reason        : {r}")
    print()

    # Evidence-classified findings
    print("FINDINGS (by evidence level and severity)")
    print("-" * 40)
    level_order = [
        "evidence_backed",
        "contradicted",
        "observed",
        "unverified_assumption",
        "agent_claim",
    ]
    by_level: dict[str, list] = {lv: [] for lv in level_order}
    for f in result.findings:
        key = (
            f.evidence_level.value if hasattr(f.evidence_level, "value") else str(f.evidence_level)
        )
        by_level.setdefault(key, []).append(f)

    labels = {
        "evidence_backed": "EVIDENCE BACKED",
        "contradicted": "CONTRADICTED",
        "observed": "OBSERVED",
        "unverified_assumption": "UNVERIFIED ASSUMPTION",
        "agent_claim": "AGENT CLAIM",
    }

    any_finding = False
    for lv in level_order:
        items = by_level.get(lv, [])
        if not items:
            continue
        any_finding = True
        print(f"  [{labels[lv]}]")
        for f in items:
            sev = (f.severity.value if hasattr(f.severity, "value") else str(f.severity)).upper()
            desc = f.description[:100]
            blocker = " ⚠ BLOCKER" if f.is_blocker() else ""
            print(f"    [{sev}]{blocker} {desc}")
            if f.suggested_action:
                print(f"    -> {f.suggested_action[:100]}")
        print()
    if not any_finding:
        print("  No findings.")
        print()

    # Contradictions
    if result.contradictions:
        print("CONTRADICTIONS")
        print("-" * 40)
        for c in result.contradictions:
            print(f"  Claim    : {c.get('claim', '')[:100]}")
            print(f"  Evidence : {c.get('description', '')[:120]}")
            print(f"  Action   : {c.get('suggested_action', '')[:100]}")
            print()

    # Unverified assumptions
    if result.unverified_assumptions:
        print("UNVERIFIED ASSUMPTIONS")
        print("-" * 40)
        for a in result.unverified_assumptions:
            print(f"  • {a[:120]}")
        print()

    # Missing evidence
    if result.missing_evidence:
        print("MISSING EVIDENCE")
        print("-" * 40)
        for m in result.missing_evidence:
            print(f"  • {m[:120]}")
        print()

    # Agent claims unchecked
    if result.agent_claims_unchecked:
        print("UNCHECKED AGENT CLAIMS")
        print("-" * 40)
        for c in result.agent_claims_unchecked:
            print(f"  • {c[:120]}")
        print()

    # Improvement priority
    print("IMPROVEMENT PRIORITY (most critical first)")
    print("-" * 40)
    if result.improvement_priority:
        for i, f in enumerate(result.improvement_priority[:8], 1):
            ev = (
                (
                    f.evidence_level.value
                    if hasattr(f.evidence_level, "value")
                    else str(f.evidence_level)
                )
                .replace("_", " ")
                .upper()
            )
            sev = (f.severity.value if hasattr(f.severity, "value") else str(f.severity)).upper()
            blocker = " ⚠ BLOCKER" if f.is_blocker() else ""
            print(f"  [{i}] [{ev}][{sev}]{blocker} {f.description[:90]}")
    else:
        print("  None -- no open findings.")
    print()

    # Skeptic summary
    print("SKEPTIC SUMMARY")
    print("-" * 40)
    print(f"  {result.skeptic_summary}")
    print()

    blockers = sum(1 for f in result.findings if f.is_blocker())
    print(sep)
    print(
        f"Blockers: {blockers} | Open Findings: {len(result.get_open_findings())} | Evidence: {result.evidence_sufficiency.level.upper()}"
    )
    print(sep)


def _run_contract_command(
    workspace_path: str, is_json: bool, task_spec_path: Optional[str] = None
) -> None:
    task_spec_dict = None
    if task_spec_path and os.path.exists(task_spec_path):
        with open(task_spec_path, encoding="utf-8") as f:
            task_spec_dict = json.load(f)

    verif_result = verify(workspace=workspace_path, task_spec=task_spec_dict)
    spec_cov = verif_result.trust_profile.get("specification_coverage", {})

    if is_json:
        print(json.dumps(spec_cov, indent=2))
    else:
        print("=" * 68)
        print("THE JUDGE v1.0.0 -- Requirement Specification Contract Report")
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
        print(
            f"Specification Escape Rate     : {summary.get('specification_escape_rate_pct', 0.0)}%"
        )
        print()

        print("REQUIREMENT DETAILS")
        print("-------------------")
        for req in spec_cov.get("requirements", []):
            st = req.get("status", "UNVERIFIED")
            symbol = (
                "OK" if st == "VERIFIED" else ("PARTIAL" if st == "PARTIALLY_VERIFIED" else "FAIL")
            )
            print(f"[{symbol}] [{st}] {req.get('id')}: {req.get('description')}")
            print(f"    Category: {req.get('category')} | Priority: {req.get('priority')}")
            if req.get("unverified_reason"):
                print(f"    Reason:   {req.get('unverified_reason')}")
            for p in req.get("mapped_properties", []):
                print(
                    f"    |-- Property: {p.get('property_name')} (Provenance: {p.get('provenance')}, Confidence: {p.get('confidence')})"
                )
            print()
        print("=" * 68)


def _print_human_readable_result(workspace_path: str, result: Any) -> None:
    print("=" * 68)
    print("THE JUDGE v1.0.0 -- Verification Report")
    print("=" * 68)
    print(f"Workspace: {os.path.abspath(workspace_path)}")
    print()

    tp = result.trust_profile
    ev_level = tp.get("evidence_level", 0)

    env_ok = (
        tp.get("environment_isolation_subdimensions", {}).get("process_isolation") == "VERIFIED"
    )
    chal_ok = (
        tp.get("evidence_integrity_subdimensions", {}).get("challenge_integrity") == "VERIFIED"
    )
    beh_ok = result.decision != "FAIL" and ev_level >= 2
    indep_ok = tp.get("evidence_integrity_subdimensions", {}).get("evidence_independence") in (
        "VERIFIED",
        "PARTIAL",
    )
    adv_ok = (
        tp.get("adversarial_robustness_subdimensions", {}).get("evasion_resistance") == "VERIFIED"
    )

    print(f"[1/5] Environment isolation       {'PASS' if env_ok else 'FAIL'}")
    print(f"[2/5] Challenge integrity         {'PASS' if chal_ok else 'FAIL'}")
    print(
        f"[3/5] Behavioral verification    {'PASS' if beh_ok else ('ABSTAIN' if result.decision == 'ABSTAIN' else 'FAIL')}"
    )
    print(f"[4/5] Evidence independence      {'PASS' if indep_ok else 'FAIL'}")
    print(f"[5/5] Adversarial checks          {'PASS' if adv_ok else 'FAIL'}")
    print()

    spec_cov = tp.get("specification_coverage", {}).get("summary", {})
    if spec_cov:
        print("SPECIFICATION COVERAGE")
        print("----------------------")
        print(f"Critical Coverage : {spec_cov.get('critical_coverage_pct', 0.0)}%")
        print(f"Overall Coverage  : {spec_cov.get('overall_coverage_pct', 0.0)}%")
        print(
            f"Verified / Total  : {spec_cov.get('verified_count', 0)} / {spec_cov.get('total_requirements', 0)}"
        )
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
    import sys

    sys.exit(main())
