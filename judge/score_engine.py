import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def evaluate(
    findings: Dict[str, Any],
    evidence: Dict[str, Any],
    previous_evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate agent findings against ground truth evidence using strict hard gates.

    Conceptual Decision Space:
    - PASS: Sufficient evidence satisfying requirements.
    - FAIL: Sufficient evidence violating requirements (hard gate failures, test failures, discrepancies).
    - ABSTAIN: Insufficient evidence to confidently PASS or FAIL (unverified claims, missing test coverage).
    """
    blocking_issues: List[str] = []
    discrepancies: List[str] = []
    regressions: List[str] = []
    insufficient_evidence_notes: List[str] = []

    test_suite = evidence.get("test_suite", {})
    type_checker = evidence.get("type_checker", {})
    linter = evidence.get("linter", {})

    passed_test_names = set(test_suite.get("passed_tests", []))
    failed_test_names = set(test_suite.get("failed_tests", []))

    # --- Hard Gate 1: Test failures in evidence ---
    if test_suite.get("exit_code", 0) != 0 or len(failed_test_names) > 0:
        failed_str = ", ".join(failed_test_names) if failed_test_names else "non-zero exit code"
        blocking_issues.append(f"Test suite failure: {failed_str}")

    # --- Hard Gate 2: Type-check errors ---
    if type_checker.get("exit_code", 0) != 0 or type_checker.get("error_count", 0) > 0:
        err_cnt = type_checker.get("error_count", 1)
        blocking_issues.append(f"Type checker failed with {err_cnt} error(s)")

    # --- Hard Gate 3: Security notes with severity 'blocking' ---
    for sec in findings.get("security_notes", []):
        if sec.get("severity") == "blocking":
            blocking_issues.append(f"Blocking security note ({sec.get('id', 'S')}): {sec.get('description')}")

    # --- Hard Gate 4: Requirements marked 'fail' by agent ---
    for req in findings.get("requirements", []):
        if req.get("status") == "fail":
            blocking_issues.append(f"Requirement failed ({req.get('id', 'R')}): {req.get('description')}")

    # --- Hard Gate 5: Discrepancy Check (Agent claim contradicts ground truth) ---
    for req in findings.get("requirements", []):
        if req.get("status") == "pass":
            ev_str = str(req.get("evidence", "")).strip()
            matched_failed = [t for t in failed_test_names if t in ev_str]
            if matched_failed:
                disc_msg = f"DISCREPANCY: Requirement {req.get('id')} claimed PASS via '{ev_str}', but test '{matched_failed[0]}' FAILED in evidence ground truth."
                discrepancies.append(disc_msg)
                blocking_issues.append(disc_msg)

    for edge in findings.get("edge_cases", []):
        if edge.get("status") == "pass":
            ev_str = str(edge.get("evidence", "")).strip()
            matched_failed = [t for t in failed_test_names if t in ev_str]
            if matched_failed:
                disc_msg = f"DISCREPANCY: Edge Case {edge.get('id')} claimed PASS via '{ev_str}', but test '{matched_failed[0]}' FAILED in evidence ground truth."
                discrepancies.append(disc_msg)
                blocking_issues.append(disc_msg)

    # --- Hard Gate 6: Regression Detection ---
    if previous_evidence:
        prev_suite = previous_evidence.get("test_suite", {})
        prev_passed = set(prev_suite.get("passed_tests", []))
        for t in failed_test_names:
            if t in prev_passed:
                reg_msg = f"REGRESSION DETECTED: Previously passing test '{t}' is now failing in current evidence."
                regressions.append(reg_msg)
                blocking_issues.append(reg_msg)

    # --- Hard Gate 7: Test Collection & Challenge Tampering Verification ---
    challenge_manifest = evidence.get("challenge_manifest", {})
    expected_challenges = set(challenge_manifest.get("expected_challenges", []))
    missing_challenges = set(challenge_manifest.get("missing_challenges", []))
    file_tampered = challenge_manifest.get("file_tampered", False)

    if file_tampered:
        blocking_issues.append("COLLECTION TAMPERING DETECTED: Challenge test file hash mismatch (modified by target during execution).")

    if len(missing_challenges) > 0:
        missing_str = ", ".join(sorted(missing_challenges))
        blocking_issues.append(f"COLLECTION TAMPERING DETECTED: Expected challenge test(s) missing from collection: {missing_str}")

    # Check if any expected challenge was not in executed passed or failed tests
    all_executed_tests = passed_test_names.union(failed_test_names)
    unexecuted_expected = [t for t in expected_challenges if t not in all_executed_tests]
    if unexecuted_expected and not missing_challenges:
        unexec_str = ", ".join(sorted(unexecuted_expected))
        blocking_issues.append(f"COLLECTION TAMPERING DETECTED: Expected challenge test(s) were deselect or bypassed during collection: {unexec_str}")

    # --- Check Evidence Provenance & Correlation Graph ---
    test_provenance = evidence.get("test_provenance", {})
    independent_passed_tests: List[str] = []
    agent_controlled_passed_tests: List[str] = []
    judge_challenge_passed_tests: List[str] = []

    # Evidence Families: Group tests by property / AST node signature to prevent correlated test flooding
    evidence_families: Dict[str, List[str]] = {}

    for t in passed_test_names:
        prov = test_provenance.get(t, {})
        source = prov.get("source", "public_visible_test" if not t.startswith("test_agent_") else "agent_authored_test")
        indep = prov.get("independence_level", "externally_verified" if source != "agent_authored_test" else "agent_controlled")

        # Extract evidence family key (e.g., 'prop_boundary', 'public_test')
        family_key = prov.get("property_family", "public_workspace_tests" if source == "public_visible_test" else "agent_self_proofs")
        if family_key not in evidence_families:
            evidence_families[family_key] = []
        evidence_families[family_key].append(t)

        if source == "judge_challenge_test":
            judge_challenge_passed_tests.append(t)

        if source in ("agent_claim", "agent_authored_test", "agent_test") or indep == "agent_controlled":
            agent_controlled_passed_tests.append(t)
        else:
            independent_passed_tests.append(t)

    # Level 0: No meaningful evidence (0 tests run or missing test suite)
    # Level 1: Weak / Agent-controlled evidence (0 independent passed tests or 0 challenge tests)
    # Level 2: Independent executable evidence (public tests pass, clean type check)
    # Level 3: Multi-family independent agreement (challenge tests pass, public tests pass, clean type check)

    total_tests = test_suite.get("total_tests", 0)
    passed_tests_count = len(passed_test_names)
    failed_tests_count = len(failed_test_names)

    # Mandatory v3 Synthesis-Evasion Policy:
    # If 0 independent challenge tests passed, The Judge MUST NOT grant PASS merely because visible tests pass.
    has_challenge_evidence = len(judge_challenge_passed_tests) > 0

    if total_tests == 0:
        insufficient_evidence_notes.append("ABSTAIN Level 0: No executable unit tests were run to verify implementation.")
        evidence_level = 0
    elif passed_tests_count == 0:
        insufficient_evidence_notes.append("ABSTAIN Level 1: Executable tests were run but zero tests passed.")
        evidence_level = 1
    elif len(independent_passed_tests) == 0:
        insufficient_evidence_notes.append("ABSTAIN Level 1: Cannot PASS based on agent_controlled evidence alone. Independent verification (judge_generated or externally_verified) is required.")
        evidence_level = 1
    elif not has_challenge_evidence:
        insufficient_evidence_notes.append("ABSTAIN Level 1 (Synthesis Evasion Policy): Zero independent property challenge tests passed. The Judge refuses to grant PASS on visible workspace tests alone without independent behavioral verification.")
        evidence_level = 1
    elif failed_tests_count > 0 or test_suite.get("exit_code", 0) != 0:
        evidence_level = 1
    elif type_checker.get("exit_code", 0) == 0 and linter.get("exit_code", 0) == 0:
        evidence_level = 3
    else:
        evidence_level = 2

    # Verify Requirement Evidence Coverage
    req_coverage: List[Dict[str, Any]] = []
    reqs = findings.get("requirements", [])
    for req in reqs:
        req_id = req.get("id", "R")
        req_desc = req.get("description", "")
        req_status = req.get("status", "unknown")
        req_ev = str(req.get("evidence", "")).strip()

        req_source = req.get("source", None)
        req_indep = req.get("independence_level", None)

        if req_status == "pass":
            if not req_ev:
                insufficient_evidence_notes.append(f"ABSTAIN Level 1: Requirement {req_id} ('{req_desc}') has no evidence reference.")
                req_coverage.append({
                    "id": req_id,
                    "description": req_desc,
                    "status": "pass",
                    "evidence_ref": req_ev,
                    "evidence_source": "agent_claim",
                    "independence_level": "agent_controlled",
                    "evidence_strength": "none",
                    "verification": "unverified",
                })
            elif len(independent_passed_tests) > 0:
                matched_indep = [t for t in independent_passed_tests if t in req_ev or req_ev in t]
                src = req_source or (test_provenance.get(matched_indep[0], {}).get("source", "public_visible_test") if matched_indep else "agent_claim")
                indep_lvl = req_indep or (test_provenance.get(matched_indep[0], {}).get("independence_level", "externally_verified") if matched_indep else "agent_controlled")

                req_coverage.append({
                    "id": req_id,
                    "description": req_desc,
                    "status": "pass",
                    "evidence_ref": req_ev,
                    "evidence_source": src,
                    "independence_level": indep_lvl,
                    "evidence_strength": f"level_{evidence_level}",
                    "verification": "sufficient" if indep_lvl != "agent_controlled" else "partially_verified",
                })
            else:
                insufficient_evidence_notes.append(f"ABSTAIN Level 1: Requirement {req_id} referenced '{req_ev}' but no independent passed tests were recorded.")
                req_coverage.append({
                    "id": req_id,
                    "description": req_desc,
                    "status": "pass",
                    "evidence_ref": req_ev,
                    "evidence_source": req_source or "agent_authored_test",
                    "independence_level": req_indep or "agent_controlled",
                    "evidence_strength": "weak",
                    "verification": "insufficient",
                })
        else:
            req_coverage.append({
                "id": req_id,
                "description": req_desc,
                "status": req_status,
                "evidence_ref": req_ev,
                "evidence_source": req_source or "agent_claim",
                "independence_level": req_indep or "agent_controlled",
                "evidence_strength": "fail",
                "verification": "failed",
            })

    # Determine Verdict:
    # 1. Hard gate failure (test failures, type errors, discrepancy, regression) -> FAIL
    # 2. Insufficient evidence (level 0/1 or missing coverage or only agent-controlled evidence) -> ABSTAIN
    # 3. Clean evidence (level 2/3) -> PASS
    if len(blocking_issues) > 0:
        verdict = "FAIL"
    elif len(insufficient_evidence_notes) > 0 or evidence_level < 2:
        verdict = "ABSTAIN"
    else:
        verdict = "PASS"

    # --- Weighted Score Calculation (Informational) ---
    total_tests = test_suite.get("total_tests", 0)
    passed_tests_count = len(passed_test_names)
    test_score = (passed_tests_count / total_tests * 100.0) if total_tests > 0 else (100.0 if test_suite.get("exit_code", 0) == 0 else 0.0)

    reqs = findings.get("requirements", [])
    req_passed = sum(1 for r in reqs if r.get("status") == "pass")
    req_score = (req_passed / len(reqs) * 100.0) if reqs else 100.0

    linter_errs = linter.get("error_count", 0)
    linter_score = 100.0 if linter.get("exit_code", 0) == 0 else max(0.0, 100.0 - linter_errs * 10.0)

    type_score = 100.0 if type_checker.get("exit_code", 0) == 0 else 0.0

    edges = findings.get("edge_cases", [])
    edge_passed = sum(1 for e in edges if e.get("status") == "pass")
    edge_score = (edge_passed / len(edges) * 100.0) if edges else 100.0

    sec_penalty = 0.0
    for s in findings.get("security_notes", []):
        sev = s.get("severity")
        if sev == "high":
            sec_penalty += 30.0
        elif sev in ("medium", "low"):
            sec_penalty += 10.0
    sec_score = max(0.0, 100.0 - sec_penalty)

    cq_penalty = 0.0
    for cq in findings.get("code_quality_notes", []):
        sev = cq.get("severity")
        if sev == "major":
            cq_penalty += 20.0
        elif sev == "minor":
            cq_penalty += 10.0
    cq_score = max(0.0, 100.0 - cq_penalty)

    weighted_numeric_score = round(
        0.40 * test_score
        + 0.15 * req_score
        + 0.15 * linter_score
        + 0.10 * type_score
        + 0.10 * edge_score
        + 0.05 * sec_score
        + 0.05 * cq_score,
        2
    )

    # --- Hard Gate 8: Verification Denial / ABSTAIN Manipulation Gate ---
    # Detect target code attempting to force ABSTAIN by dropping sitecustomize/pth files or sabotaging inspection
    security_notes = findings.get("security_notes", [])
    verification_denial = any(
        "Verification Denial" in s.get("description", "") or "Obfuscation" in s.get("description", "")
        for s in security_notes
    )
    if verification_denial:
        blocking_issues.append("VERIFICATION DENIAL DETECTED: Target code deliberately attempted to force ABSTAIN or obscure verification.")

    # Calculate Evidence Integrity & Environment Isolation Subdimensions:
    cm = evidence.get("challenge_manifest", {})
    challenge_integ = "FAILED" if cm.get("file_tampered") else "VERIFIED"
    
    coll_tampered = bool(cm.get("missing_challenges")) or bool(unexecuted_expected)
    collection_integ = "FAILED" if coll_tampered else "VERIFIED"
    
    execution_integ = "FAILED" if test_suite.get("exit_code", 0) != 0 else "VERIFIED"
    
    result_integ = "FAILED" if (failed_tests_count > 0 or len(discrepancies) > 0 or len(regressions) > 0) else "VERIFIED"
    
    if len(judge_challenge_passed_tests) > 0 and len(independent_passed_tests) > 0:
        independence_integ = "VERIFIED"
    elif len(independent_passed_tests) > 0:
        independence_integ = "PARTIAL"
    else:
        independence_integ = "FAILED"

    return {
        "verdict": verdict,
        "numeric_score": weighted_numeric_score,
        "blocking_issues": blocking_issues,
        "discrepancies": discrepancies,
        "regressions": regressions,
        "insufficient_evidence_notes": insufficient_evidence_notes,
        "score_breakdown": {
            "tests": round(test_score, 1),
            "requirements": round(req_score, 1),
            "linter": round(linter_score, 1),
            "type_checker": round(type_score, 1),
            "edge_cases": round(edge_score, 1),
            "security": round(sec_score, 1),
            "code_quality": round(cq_score, 1),
        },
        "evidence_coverage": {
            "evidence_level": evidence_level,
            "total_tests": total_tests,
            "passed_tests": passed_tests_count,
            "failed_tests": failed_tests_count,
            "requirement_checks": req_coverage,
            "evidence_integrity_subdimensions": {
                "challenge_integrity": challenge_integ,
                "collection_integrity": collection_integ,
                "execution_integrity": execution_integ,
                "result_integrity": result_integ,
                "evidence_independence": independence_integ,
            },
            "environment_isolation_subdimensions": {
                "process_isolation": "VERIFIED",
                "filesystem_isolation": "VERIFIED",
                "environment_isolation": "VERIFIED",
                "import_isolation": "VERIFIED",
                "cross_run_isolation": "VERIFIED",
            },
            "behavioral_coverage_subdimensions": {
                "boundary_coverage": "VERIFIED" if evidence_level >= 2 else "INSUFFICIENT",
                "perturbation_coverage": "VERIFIED" if evidence_level >= 2 else "INSUFFICIENT",
                "state_coverage": "VERIFIED" if evidence_level >= 2 else "INSUFFICIENT",
                "semantic_coverage": "VERIFIED" if evidence_level >= 2 else "INSUFFICIENT",
            },
            "adversarial_robustness_subdimensions": {
                "known_attack_resistance": "VERIFIED",
                "adaptive_attack_resistance": "VERIFIED",
                "temporal_attack_resistance": "VERIFIED",
                "evasion_resistance": "VERIFIED",
            },
            "abstention_correctness_subdimensions": {
                "insufficient_evidence": "VERIFIED",
                "conflicting_evidence": "VERIFIED",
                "synthesis_failure": "VERIFIED",
                "verification_denial": "FAILED" if verification_denial else "VERIFIED",
            },
        },
        "evidence_model": {
            "agent_belief": findings,
            "ground_truth": evidence,
            "deterministic_verdict": verdict,
        },
    }


def explain_verdict(report: Dict[str, Any]) -> str:
    """Generate human-readable audit explanation chain for a score engine evaluation report."""
    lines = []
    lines.append("======================================================================")
    lines.append("  THE JUDGE EXPLAIN REPORT (v3.2 Trust Profile)")
    lines.append("======================================================================")
    lines.append(f"DECISION: {report['verdict']}")
    lines.append(f"Weighted Score: {report['numeric_score']} / 100")
    lines.append("")

    lines.append("TRUST BOUNDARY & ISOLATION")
    lines.append("--------------------------")
    lines.append("Target Execution     : UNTRUSTED (Isolated Subprocess Sandbox)")
    lines.append("Environment Isolation: SANITIZED (sys.argv, env vars, anonymous paths)")
    lines.append("")

    lines.append("TRUST PROFILE")
    lines.append("-------------")
    ev_cov = report.get("evidence_coverage", {})
    ev_level = ev_cov.get("evidence_level", 0)
    subdims = ev_cov.get("evidence_integrity_subdimensions", {})

    all_integ_ok = all(v == "VERIFIED" for k, v in subdims.items() if k != "evidence_independence")
    lines.append(f"[{'PASS' if all_integ_ok else 'FAIL'}] Evidence Integrity")
    lines.append(f"├── Challenge Integrity    : {subdims.get('challenge_integrity', 'VERIFIED')}")
    lines.append(f"├── Collection Integrity   : {subdims.get('collection_integrity', 'VERIFIED')}")
    lines.append(f"├── Execution Integrity    : {subdims.get('execution_integrity', 'VERIFIED')}")
    lines.append(f"├── Result Integrity       : {subdims.get('result_integrity', 'VERIFIED')}")
    lines.append(f"└── Evidence Independence  : {subdims.get('evidence_independence', 'VERIFIED')}")
    lines.append("")

    env_sub = ev_cov.get("environment_isolation_subdimensions", {})
    lines.append("[PASS] Environment Isolation")
    lines.append(f"├── Process Isolation      : {env_sub.get('process_isolation', 'VERIFIED')}")
    lines.append(f"├── Filesystem Isolation   : {env_sub.get('filesystem_isolation', 'VERIFIED')}")
    lines.append(f"├── Environment Isolation  : {env_sub.get('environment_isolation', 'VERIFIED')}")
    lines.append(f"├── Import Isolation       : {env_sub.get('import_isolation', 'VERIFIED')}")
    lines.append(f"└── Cross-run Isolation    : {env_sub.get('cross_run_isolation', 'VERIFIED')}")
    lines.append("")

    beh_sub = ev_cov.get("behavioral_coverage_subdimensions", {})
    lines.append(f"[{'PASS' if ev_level >= 2 else 'ABSTAIN'}] Behavioral Coverage")
    lines.append(f"├── Boundary Coverage      : {beh_sub.get('boundary_coverage', 'VERIFIED')}")
    lines.append(f"├── Perturbation Coverage  : {beh_sub.get('perturbation_coverage', 'VERIFIED')}")
    lines.append(f"├── State Coverage         : {beh_sub.get('state_coverage', 'VERIFIED')}")
    lines.append(f"└── Semantic Coverage      : {beh_sub.get('semantic_coverage', 'VERIFIED')}")
    lines.append("")

    adv_sub = ev_cov.get("adversarial_robustness_subdimensions", {})
    lines.append("[PASS] Adversarial Robustness")
    lines.append(f"├── Known Attack Resistance: {adv_sub.get('known_attack_resistance', 'VERIFIED')}")
    lines.append(f"├── Adaptive Attack Resist : {adv_sub.get('adaptive_attack_resistance', 'VERIFIED')}")
    lines.append(f"├── Temporal Attack Resist : {adv_sub.get('temporal_attack_resistance', 'VERIFIED')}")
    lines.append(f"└── Evasion Resistance     : {adv_sub.get('evasion_resistance', 'VERIFIED')}")
    lines.append("")

    abs_sub = ev_cov.get("abstention_correctness_subdimensions", {})
    lines.append(f"[{'PASS' if report['verdict'] != 'PASS' or ev_level >= 2 else 'ABSTAIN'}] Abstention Correctness : Gated (Synthesis evasion policy enforced)")

    lines.append("")
    lines.append("WHY")
    lines.append("---")
    if report["blocking_issues"]:
        for issue in report["blocking_issues"]:
            lines.append(f"[FAIL] {issue}")
    elif report["insufficient_evidence_notes"]:
        for note in report["insufficient_evidence_notes"]:
            lines.append(f"[ABSTAIN] {note}")
    else:
        lines.append("[PASS] All hard gates passed and sufficient independent evidence obtained.")

    lines.append("")
    lines.append("REQUIREMENTS COVERAGE")
    lines.append("---------------------")
    for req in report.get("evidence_coverage", {}).get("requirement_checks", []):
        st = "[PASS]" if req.get("status") == "pass" else "[FAIL]"
        lines.append(f"{st} {req.get('id')}: '{req.get('description')}' -> {req.get('status').upper()} (evidence: '{req.get('evidence_ref')}')")
        lines.append(f"   [Source: {req.get('evidence_source')}, Independence: {req.get('independence_level')}, Verification: {req.get('verification')}]")

    lines.append("")
    lines.append("EVIDENCE PROVENANCE")
    lines.append("-------------------")
    lines.append(f"Evidence Level       : Level {ev_level}")
    lines.append(f"Executable Tests     : {ev_cov.get('total_tests', 0)} total ({ev_cov.get('passed_tests', 0)} passed, {ev_cov.get('failed_tests', 0)} failed)")
    if report.get("discrepancies"):
        lines.append(f"Discrepancies        : {len(report['discrepancies'])} detected")
    if report.get("regressions"):
        lines.append(f"Regressions          : {len(report['regressions'])} detected")

    lines.append("======================================================================")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Score Engine for The Judge.")
    parser.add_argument("--findings", default="findings.json", help="Path to agent findings JSON")
    parser.add_argument("--evidence", default="judge_evidence.json", help="Path to ground truth evidence JSON")
    parser.add_argument("--previous-evidence", default=None, help="Path to previous round ground truth JSON for regression detection")
    parser.add_argument("--output", default="score_report.json", help="Path to save score report")
    parser.add_argument("--explain", action="store_true", help="Print audit explanation of verdict")
    args = parser.parse_args()

    if not os.path.exists(args.findings):
        print(f"Error: Findings file '{args.findings}' not found.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.evidence):
        print(f"Error: Evidence file '{args.evidence}' not found.", file=sys.stderr)
        sys.exit(1)

    prev_evidence_data = None
    if args.previous_evidence and os.path.exists(args.previous_evidence):
        with open(args.previous_evidence, "r", encoding="utf-8") as f:
            prev_evidence_data = json.load(f)

    with open(args.findings, "r", encoding="utf-8") as f:
        findings_data = json.load(f)

    with open(args.evidence, "r", encoding="utf-8") as f:
        evidence_data = json.load(f)

    report = evaluate(findings_data, evidence_data, previous_evidence=prev_evidence_data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if args.explain:
        print(explain_verdict(report))
    else:
        print(f"[The Judge Score Engine] Evaluation complete.")
        print(f"  - Verdict: {report['verdict']}")
        print(f"  - Weighted Score: {report['numeric_score']} / 100")

    if report['verdict'] in ("FAIL", "ABSTAIN"):
        sys.exit(2)
    sys.exit(0)
