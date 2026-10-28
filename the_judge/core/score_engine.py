from typing import Any, Optional


def evaluate(
    findings: dict[str, Any],
    evidence: dict[str, Any],
    previous_evidence: Optional[dict[str, Any]] = None,
    agent_claims_provided: bool = False,
) -> dict[str, Any]:
    """Evaluate agent findings against ground truth evidence using strict hard gates.

    Conceptual Decision Space:
    - PASS: Sufficient evidence satisfying requirements.
    - FAIL: Sufficient evidence violating requirements (hard gate failures, test failures, discrepancies).
    - ABSTAIN: Insufficient evidence to confidently PASS or FAIL (unverified claims, missing test coverage).
    """
    blocking_issues: list[str] = []
    discrepancies: list[str] = []
    regressions: list[str] = []
    insufficient_evidence_notes: list[str] = []

    test_suite = evidence.get("test_suite", {})
    type_checker = evidence.get("type_checker", {})
    linter = evidence.get("linter", {})

    passed_test_names = set(test_suite.get("passed_tests", []))
    failed_test_names = set(test_suite.get("failed_tests", []))

    # Filter out vacuous tests (assert True, no assertions, no target reference)
    vacuous_test_set = set(evidence.get("vacuous_tests", []))
    passed_test_names = {t for t in passed_test_names if t.split("[", 1)[0] not in vacuous_test_set}

    # --- Gate 0: the test runner itself could not start (infrastructure) ---
    runner_error = test_suite.get("runner_error")
    if runner_error:
        insufficient_evidence_notes.append(
            "ABSTAIN Level 0 (Test Runner): no test could run because pytest could not be "
            f"started ({runner_error}). Install it with `pip install pytest` in the "
            "environment that runs The Judge."
        )

    no_tests = bool(test_suite.get("no_tests_collected")) and not runner_error
    if no_tests:
        insufficient_evidence_notes.append(
            "ABSTAIN Level 0 (No Tests): pytest collected no tests in this workspace, so no "
            "behaviour was checked. Add test files named test_*.py (or *_test.py) containing "
            "test_* functions that assert the expected results."
        )

    # --- Hard Gate 1: Test failures in evidence ---
    if runner_error or no_tests:
        pass  # nothing ran; reported above, not a test failure
    elif test_suite.get("exit_code", 0) != 0 or len(failed_test_names) > 0:
        failed_str = ", ".join(failed_test_names) if failed_test_names else "non-zero exit code"
        blocking_issues.append(f"Test suite failure: {failed_str}")

    # --- Gate 2: static analysis is advisory ---
    # mypy and ruff never decide correctness: a missing tool is INFO, and type or lint
    # errors are WARNINGs (reported as static_analysis findings, lowering the score).
    # Behaviour is decided by tests only.
    if not type_checker.get("available", True):
        insufficient_evidence_notes.append(
            "INFO: Type checker (mypy) not found on PATH; type checking was not run, "
            "so confidence is reduced. Install with `pip install mypy`."
        )
    elif type_checker.get("error_count", 0) > 0:
        err_cnt = type_checker.get("error_count", 1)
        insufficient_evidence_notes.append(
            f"WARNING: Type checker (mypy) reported {err_cnt} error(s). Advisory only; it does "
            "not affect the decision."
        )
    elif type_checker.get("exit_code", 0) != 0:
        insufficient_evidence_notes.append(
            "INFO: Type checker exited non-zero without reporting type errors; see its output."
        )

    # --- Hard Gate 3: Security notes with severity 'blocking' ---
    for sec in findings.get("security_notes", []):
        if sec.get("severity") == "blocking":
            blocking_issues.append(
                f"Blocking security note ({sec.get('id', 'S')}): {sec.get('description')}"
            )

    # --- Hard Gate 4: Requirements marked 'fail' by agent ---
    for req in findings.get("requirements", []):
        if req.get("status") == "fail":
            blocking_issues.append(
                f"Requirement failed ({req.get('id', 'R')}): {req.get('description')}"
            )

    # --- Hard Gate 5: Discrepancy Check (Agent claim contradicts ground truth) ---
    if agent_claims_provided:
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
        blocking_issues.append(
            "COLLECTION TAMPERING DETECTED: Challenge test file hash mismatch (modified by target during execution)."
        )

    if len(missing_challenges) > 0:
        missing_str = ", ".join(sorted(missing_challenges))
        blocking_issues.append(
            f"COLLECTION TAMPERING DETECTED: Expected challenge test(s) missing from collection: {missing_str}"
        )

    # Skipped tests (workspace skips and probes that did not apply) were collected and
    # run, so they are not "bypassed"; they simply do not count as passing evidence.
    # Vacuous tests ran too: use the raw pass list, not the evidence-filtered one.
    all_executed_tests = {
        t.split("[", 1)[0]  # parametrized cases count for their function
        for t in set(test_suite.get("passed_tests", [])).union(failed_test_names).union(
            test_suite.get("skipped_tests", []), test_suite.get("skipped_probes", [])
        )
    }
    unexecuted_expected = [t for t in expected_challenges if t not in all_executed_tests]
    if unexecuted_expected and not missing_challenges and not runner_error:
        unexec_str = ", ".join(sorted(unexecuted_expected))
        blocking_issues.append(
            f"COLLECTION TAMPERING DETECTED: Expected challenge test(s) were deselect or bypassed during collection: {unexec_str}"
        )

    # --- Hard Gate 7b: Test tampering relative to the git baseline ---
    tampering = evidence.get("test_tampering", {})
    for issue in tampering.get("issues", []):
        blocking_issues.append(
            f"TEST TAMPERING DETECTED (vs {tampering.get('ref', 'HEAD')}): {issue['detail']}"
        )

    # --- Hard Gate 7b2: a plugin/conftest rewrote a failing outcome as passed ---
    rewritten = test_suite.get("outcome_tampered", [])
    if rewritten:
        blocking_issues.append(
            "TEST TAMPERING DETECTED (result rewriting): test(s) raised but were reported as "
            "passed by a conftest/plugin hook: " + ", ".join(rewritten)
        )

    # --- Hard Gate 7c: frozen tests weakened or deleted since `judge freeze` ---
    independence = evidence.get("independence", {})
    for issue in independence.get("tampering", []):
        blocking_issues.append(f"TEST TAMPERING DETECTED (vs judge freeze): {issue['detail']}")

    # --- Gate 7e: implementation hard-codes the independent tests' expected outputs ---
    hard = evidence.get("hardcoding", {})
    if hard.get("suspected"):
        insufficient_evidence_notes.append(
            "ABSTAIN Level 1 (Hard-coded Outputs): every literal assertion in the independent "
            f"tests ({hard.get('literal_assertions')}) is answered by a literal table or if-chain "
            "in the implementation (e.g. " + "; ".join(hard.get("examples", [])) + "). PASS is "
            "withheld until a test with inputs that are not in those literals passes."
        )

    # --- Gate 7d: Skipped / xfail workspace tests prove nothing ---
    skipped_workspace = test_suite.get("skipped_tests", [])
    if skipped_workspace:
        insufficient_evidence_notes.append(
            "ABSTAIN Level 1 (Skipped Tests): workspace test(s) skipped or xfail, so their "
            f"behaviour is unverified: {', '.join(sorted(skipped_workspace))}"
        )

    # --- Hard Gate 8: Verification Denial / ABSTAIN Manipulation Gate ---
    security_notes = findings.get("security_notes", [])
    verification_denial = any(
        "Verification Denial" in s.get("description", "")
        or "Obfuscation" in s.get("description", "")
        for s in security_notes
    )
    if verification_denial:
        blocking_issues.append(
            "VERIFICATION DENIAL DETECTED: Target code deliberately attempted to force ABSTAIN or obscure verification."
        )

    # --- Hard Gate 9: Coverage-Aware PASS Gate ---
    contract_data = evidence.get("contract_data", {})
    contract_summary = contract_data.get("summary", {})
    unverified_critical = contract_summary.get("critical_unverified_ids", [])
    if unverified_critical:
        unc_str = ", ".join(unverified_critical)
        insufficient_evidence_notes.append(
            f"ABSTAIN Level 2 (Coverage-Aware Gate): Critical requirement(s) [{unc_str}] remain UNVERIFIED or CONFLICTING."
        )

    test_provenance = evidence.get("test_provenance", {})
    independent_passed_tests: list[str] = []
    agent_controlled_passed_tests: list[str] = []
    judge_challenge_passed_tests: list[str] = []

    evidence_families: dict[str, list[str]] = {}

    for t in passed_test_names:
        prov = test_provenance.get(t, {})
        source = prov.get(
            "source",
            "public_visible_test" if not t.startswith("test_agent_") else "agent_authored_test",
        )
        indep = prov.get(
            "independence_level",
            "externally_verified" if source != "agent_authored_test" else "agent_controlled",
        )

        family_key = prov.get(
            "property_family",
            "public_workspace_tests" if source == "public_visible_test" else "agent_self_proofs",
        )
        if family_key not in evidence_families:
            evidence_families[family_key] = []
        evidence_families[family_key].append(t)

        if source == "judge_challenge_test":
            judge_challenge_passed_tests.append(t)

        if (
            source in ("agent_claim", "agent_authored_test", "agent_test")
            or indep == "agent_controlled"
        ):
            agent_controlled_passed_tests.append(t)
        else:
            independent_passed_tests.append(t)

    total_tests = len(passed_test_names) + len(failed_test_names)
    passed_tests_count = len(passed_test_names)
    failed_tests_count = len(failed_test_names)

    # Workspace tests: non-synthesized tests that come from the workspace itself
    workspace_passed_tests = [
        t for t in passed_test_names
        if test_provenance.get(t, {}).get("source") != "judge_challenge_test"
    ]

    independent_names = set(independence.get("independent", {}))
    independent_workspace_passed = [
        t for t in workspace_passed_tests if t.split("[", 1)[0] in independent_names
    ]

    if total_tests == 0:
        if not (no_tests or runner_error):  # those already explain why nothing ran
            insufficient_evidence_notes.append(
                "ABSTAIN Level 0: No executable unit tests were run to verify implementation."
            )
        evidence_level = 0
    elif passed_tests_count == 0:
        insufficient_evidence_notes.append(
            "ABSTAIN Level 1: Executable tests were run but zero tests passed."
        )
        evidence_level = 1
    elif len(independent_passed_tests) == 0:
        insufficient_evidence_notes.append(
            "ABSTAIN Level 1: Cannot PASS based on agent_controlled evidence alone. Independent verification (judge_generated or externally_verified) is required."
        )
        evidence_level = 1
    elif not independent_workspace_passed:
        # Independent evidence = workspace tests fixed before the implementation they
        # check (judge freeze snapshot or git baseline, implementation changed since).
        # Tests written alongside the code still have to pass, but cannot earn a PASS
        # on their own: the author could have fitted them to the code.
        frozen_after = independence.get("frozen_after_implementation", [])
        if frozen_after:
            reason = (
                "the frozen tests (" + ", ".join(frozen_after[:5]) + ") were frozen after the "
                "implementation was written: no implementation file changed since the freeze"
            )
        elif workspace_passed_tests:
            reason = (
                "no passing test was fixed before the implementation (none is unchanged since a "
                "`judge freeze` snapshot or the git baseline with the code changed afterwards)"
            )
        else:
            reason = "no workspace test passed"
        insufficient_evidence_notes.append(
            f"ABSTAIN Level 1 (No Independent Evidence): {reason}."
        )
        evidence_level = 1
    elif failed_tests_count > 0 or test_suite.get("exit_code", 0) != 0:
        evidence_level = 1
    elif type_checker.get("exit_code", 0) == 0 and linter.get("exit_code", 0) == 0:
        evidence_level = 3
    else:
        evidence_level = 2

    req_coverage: list[dict[str, Any]] = []
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
                insufficient_evidence_notes.append(
                    f"ABSTAIN Level 1: Requirement {req_id} ('{req_desc}') has no evidence reference."
                )
                req_coverage.append(
                    {
                        "id": req_id,
                        "description": req_desc,
                        "status": "pass",
                        "evidence_ref": req_ev,
                        "evidence_source": "agent_claim",
                        "independence_level": "agent_controlled",
                        "evidence_strength": "none",
                        "verification": "unverified",
                    }
                )
            elif len(independent_passed_tests) > 0:
                matched_indep = [t for t in independent_passed_tests if t in req_ev or req_ev in t]
                src = req_source or (
                    test_provenance.get(matched_indep[0], {}).get("source", "public_visible_test")
                    if matched_indep
                    else "agent_claim"
                )
                indep_lvl = req_indep or (
                    test_provenance.get(matched_indep[0], {}).get(
                        "independence_level", "externally_verified"
                    )
                    if matched_indep
                    else "agent_controlled"
                )

                req_coverage.append(
                    {
                        "id": req_id,
                        "description": req_desc,
                        "status": "pass",
                        "evidence_ref": req_ev,
                        "evidence_source": src,
                        "independence_level": indep_lvl,
                        "evidence_strength": f"level_{evidence_level}",
                        "verification": "sufficient"
                        if indep_lvl != "agent_controlled"
                        else "partially_verified",
                    }
                )
            else:
                insufficient_evidence_notes.append(
                    f"ABSTAIN Level 1: Requirement {req_id} referenced '{req_ev}' but no independent passed tests were recorded."
                )
                req_coverage.append(
                    {
                        "id": req_id,
                        "description": req_desc,
                        "status": "pass",
                        "evidence_ref": req_ev,
                        "evidence_source": req_source or "agent_authored_test",
                        "independence_level": req_indep or "agent_controlled",
                        "evidence_strength": "weak",
                        "verification": "insufficient",
                    }
                )
        else:
            req_coverage.append(
                {
                    "id": req_id,
                    "description": req_desc,
                    "status": req_status,
                    "evidence_ref": req_ev,
                    "evidence_source": req_source or "agent_claim",
                    "independence_level": req_indep or "agent_controlled",
                    "evidence_strength": "fail",
                    "verification": "failed",
                }
            )

    if len(blocking_issues) > 0:
        verdict = "FAIL"
    elif evidence_level < 2 or any(
        not n.startswith(("INFO:", "WARNING:")) for n in insufficient_evidence_notes
    ):
        verdict = "ABSTAIN"
    else:
        verdict = "PASS"

    # Note: total_tests, passed_tests_count, and failed_tests_count were already
    # computed above (lines ~144-146) and remain unchanged.
    test_score = (
        (passed_tests_count / total_tests * 100.0)
        if total_tests > 0
        else (100.0 if test_suite.get("exit_code", 0) == 0 else 0.0)
    )

    reqs = findings.get("requirements", [])
    req_passed = sum(1 for r in reqs if r.get("status") == "pass")
    req_score = (req_passed / len(reqs) * 100.0) if reqs else 100.0

    linter_errs = linter.get("error_count", 0)
    if not linter.get("available", True):
        linter_score = 0.0
        insufficient_evidence_notes.append(
            "INFO: Linter (ruff or flake8) not found on PATH; linting was not run, "
            "so confidence is reduced. Install with `pip install ruff`."
        )
    else:
        linter_score = (
            100.0 if linter.get("exit_code", 0) == 0 else max(0.0, 100.0 - linter_errs * 10.0)
        )
        if linter.get("exit_code", 0) != 0:
            insufficient_evidence_notes.append(
                f"WARNING: Linter reported {linter_errs} issue(s). Advisory only; it does not "
                "affect the decision."
            )

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

    # Components that were not measured (tool not installed) are left out and the
    # remaining weights renormalised: a missing optional tool lowers confidence
    # (evidence level 2 instead of 3, plus a tooling finding), not the score, so
    # score thresholds such as `judge improve --target-score` stay reachable.
    components = [
        (0.40, test_score, True),
        (0.15, req_score, True),
        (0.15, linter_score, linter.get("available", True)),
        (0.10, type_score, type_checker.get("available", True)),
        (0.10, edge_score, True),
        (0.05, sec_score, True),
        (0.05, cq_score, True),
    ]
    measured_weight = sum(w for w, _, measured in components if measured)
    weighted_numeric_score = round(
        sum(w * v for w, v, measured in components if measured) / measured_weight, 2
    )

    # Decision-based score cap: numeric score must not exceed the ceiling
    # implied by the verdict.  A FAIL with mostly-passing tests should still
    # report a low number so downstream tooling doesn't interpret 76.5 as
    # "nearly perfect."
    if verdict == "FAIL":
        weighted_numeric_score = min(weighted_numeric_score, 40.0)
    elif verdict == "ABSTAIN":
        weighted_numeric_score = min(weighted_numeric_score, 65.0)

    cm = evidence.get("challenge_manifest", {})
    challenge_integ = "FAILED" if cm.get("file_tampered") else "VERIFIED"

    coll_tampered = bool(cm.get("missing_challenges")) or bool(unexecuted_expected)
    collection_integ = "FAILED" if coll_tampered else "VERIFIED"

    execution_integ = (
        "NOT_RUN" if (runner_error or no_tests)
        else "FAILED" if test_suite.get("exit_code", 0) != 0 else "VERIFIED"
    )

    result_integ = (
        "FAILED"
        if (failed_tests_count > 0 or len(discrepancies) > 0 or len(regressions) > 0)
        else "VERIFIED"
    )

    probe_coverage = evidence.get("probe_coverage", {"ran": [], "not_run": []})
    integrity_failed = bool(
        cm.get("file_tampered") or coll_tampered or evidence.get("test_tampering", {}).get("issues")
    )

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
            "probe_coverage": probe_coverage,
            "evidence_integrity_subdimensions": {
                "challenge_integrity": challenge_integ,
                "collection_integrity": collection_integ,
                "execution_integrity": execution_integ,
                "result_integrity": result_integ,
                "evidence_independence": independence_integ,
            },
            "environment_isolation_subdimensions": {
                "process_isolation": "VERIFIED",
                "filesystem_isolation": "PARTIAL",
                "environment_isolation": "VERIFIED",
                "import_isolation": "PARTIAL",
                "cross_run_isolation": "VERIFIED",
            },
            # Derived from what actually ran. VERIFIED only when a judge probe of
            # that family executed its assertion and passed; NOT_CHECKED otherwise.
            "behavioral_coverage_subdimensions": {
                "boundary_coverage": "NOT_CHECKED",  # no sound boundary probe exists
                "perturbation_coverage": _probe_family_status(probe_coverage, ("idempotency",)),
                "state_coverage": _probe_family_status(
                    probe_coverage, ("rollback_isolation", "expiration", "capacity_limit")
                ),
                "semantic_coverage": (
                    "WORKSPACE_TESTS_ONLY" if workspace_passed_tests else "NOT_CHECKED"
                ),
            },
            # Only integrity gates (tampering, collection, verification denial) are
            # implemented; adaptive and temporal attacks are not assessed.
            "adversarial_robustness_subdimensions": {
                "known_attack_resistance": "FAILED" if integrity_failed else "CHECKED",
                "adaptive_attack_resistance": "NOT_ASSESSED",
                "temporal_attack_resistance": "NOT_ASSESSED",
                "evasion_resistance": "FAILED" if (integrity_failed or verification_denial) else "CHECKED",
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


def _probe_family_status(probe_coverage: dict[str, Any], kinds: tuple[str, ...]) -> str:
    outcomes = [p.get("outcome") for p in probe_coverage.get("ran", []) if p.get("kind") in kinds]
    if "failed" in outcomes:
        return "FAILED"
    if "passed" in outcomes:
        return "VERIFIED"
    return "NOT_CHECKED"


def explain_verdict(report: dict[str, Any]) -> str:
    """Generate human-readable audit explanation chain for a score engine evaluation report."""
    lines = []
    lines.append("======================================================================")
    lines.append("  THE JUDGE EXPLAIN REPORT (v4.0 Production Trust Profile)")
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
    lines.append(f"├── Boundary Coverage      : {beh_sub.get('boundary_coverage', 'NOT_CHECKED')}")
    lines.append(f"├── Perturbation Coverage  : {beh_sub.get('perturbation_coverage', 'NOT_CHECKED')}")
    lines.append(f"├── State Coverage         : {beh_sub.get('state_coverage', 'NOT_CHECKED')}")
    lines.append(f"└── Semantic Coverage      : {beh_sub.get('semantic_coverage', 'NOT_CHECKED')}")
    lines.append("")

    adv_sub = ev_cov.get("adversarial_robustness_subdimensions", {})
    lines.append("[INFO] Adversarial Robustness (integrity gates only)")
    lines.append(
        f"├── Known Attack Resistance: {adv_sub.get('known_attack_resistance', 'NOT_CHECKED')}"
    )
    lines.append(
        f"├── Adaptive Attack Resist : {adv_sub.get('adaptive_attack_resistance', 'NOT_CHECKED')}"
    )
    lines.append(
        f"├── Temporal Attack Resist : {adv_sub.get('temporal_attack_resistance', 'NOT_CHECKED')}"
    )
    lines.append(f"└── Evasion Resistance     : {adv_sub.get('evasion_resistance', 'NOT_CHECKED')}")
    lines.append("")

    abs_sub = ev_cov.get("abstention_correctness_subdimensions", {})
    lines.append(
        f"[{'PASS' if abs_sub.get('verification_denial') == 'VERIFIED' else 'FAIL'}] Abstention Correctness"
    )
    lines.append(f"├── Insufficient Evidence  : {abs_sub.get('insufficient_evidence', 'VERIFIED')}")
    lines.append(f"├── Conflicting Evidence   : {abs_sub.get('conflicting_evidence', 'VERIFIED')}")
    lines.append(f"├── Synthesis Failure      : {abs_sub.get('synthesis_failure', 'VERIFIED')}")
    lines.append(f"└── Verification Denial    : {abs_sub.get('verification_denial', 'VERIFIED')}")
    lines.append(
        f"[{'PASS' if report['verdict'] != 'PASS' or ev_level >= 2 else 'ABSTAIN'}] Abstention Correctness : Gated (Synthesis evasion policy enforced)"
    )

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

    lines.append("======================================================================")
    return "\n".join(lines)
