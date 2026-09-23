import hashlib
import os
import time
from pathlib import Path
from typing import Any, Optional

from the_judge.core.decision import Finding, VerificationResult
from the_judge.core.evidence import capture_evidence
from the_judge.core.score_engine import evaluate


def critique(
    workspace: str,
    task_spec: Optional[dict[str, Any]] = None,
    previous_round: Optional[dict[str, Any]] = None,
) -> Any:
    """Run an independent adversarial critique of the workspace.

    Unlike verify(), which confirms the Judge's hard gates, critique() asks:

      - What is wrong with this work?
      - What is weak or missing?
      - What has not been demonstrated?
      - What assumptions are being made?
      - What could fail in practice?
      - What would a skeptical expert challenge?
      - What claims are unsupported?
      - What evidence contradicts the agent?
      - What should be tested next?
      - What improvement would have the highest impact?

    Every finding is classified by evidence level:

      EVIDENCE_BACKED       — concrete evidence: test failure, log, benchmark
      OBSERVED              — directly visible in the artefact, not formally tested
      UNVERIFIED_ASSUMPTION — agent relies on something not demonstrated
      AGENT_CLAIM           — agent asserts something with no independent backing
      CONTRADICTED          — agent claims X, evidence shows not-X

    Evidence level and severity are independent dimensions:
      EVIDENCE_BACKED + LOW does NOT block the loop.
      CONTRADICTED + CRITICAL ALWAYS blocks the loop.

    The agent's explanation is NEVER treated as proof.

    Args:
        workspace: Path to directory or source file to critique.
        task_spec: Optional task specification for contract-based critique.
        previous_round: Optional previous round record for cross-round comparison.

    Returns:
        CritiqueResult containing classified findings, contradictions,
        improvement priority, and evidence sufficiency assessment.
    """
    from the_judge.core.critique_engine import CritiqueEngine

    workspace_path = os.path.abspath(workspace)
    # Capture evidence once and reuse for both verify() and critique().
    # Previously, capture_evidence() was called here AND inside verify(),
    # causing two full sandbox executions per `judge critique` invocation.
    ground_truth = capture_evidence(workspace_path, task_spec=task_spec)
    verification_result = verify(
        workspace=workspace,
        task_spec=task_spec,
        _ground_truth=ground_truth,  # pass pre-captured evidence
    )

    engine = CritiqueEngine()
    return engine.critique(
        workspace=workspace_path,
        verification_result=verification_result,
        ground_truth=ground_truth,
        previous_round=previous_round,
    )


def verify(
    workspace: str,
    task_spec: Optional[dict[str, Any]] = None,
    previous_evidence: Optional[dict[str, Any]] = None,
    _ground_truth: Optional[dict[str, Any]] = None,
) -> VerificationResult:
    """Verify code within a workspace against behavioral contracts, dynamic property checks,
    and adversarial integrity gates.

    Args:
        workspace: Path to directory or python source file to evaluate.
        task_spec: Task specification contract dictionary (or loaded task contract).
        previous_evidence: Previous evidence snapshot from an earlier round (for regression tracking).
        _ground_truth: Pre-captured evidence dict. When provided, skips capture_evidence()
            (used by critique() to avoid running the sandbox twice).

    Returns:
        VerificationResult containing structured decision, findings, trust profile, and provenance.
    """
    start_time = time.time()
    workspace_path = os.path.abspath(workspace)

    # 1. Capture ground truth evidence (sandbox execution, challenge runner, dynamic property checks)
    ground_truth = (
        _ground_truth
        if _ground_truth is not None
        else capture_evidence(workspace_path, task_spec=task_spec)
    )

    # 2. Build Agent Findings / Claims
    test_suite = ground_truth.get("test_suite", {})
    passed_tests = test_suite.get("passed_tests", [])
    failed_tests = test_suite.get("failed_tests", [])

    req_list: list[dict[str, Any]] = []

    if task_spec and "requirements" in task_spec:
        for idx, req in enumerate(task_spec.get("requirements", []), 1):
            req_id = req.get("id", f"REQ-{idx:03d}")
            req_desc = req.get("description", "")
            # Check if any failed test corresponds to this requirement
            has_fail = any(req_id.lower() in t.lower() or "fail" in t.lower() for t in failed_tests)
            req_status = "fail" if has_fail else ("pass" if len(passed_tests) > 0 else "unknown")
            ev_ref = (
                f"test_{req_id.lower()}" if has_fail else (passed_tests[0] if passed_tests else "")
            )
            req_list.append(
                {
                    "id": req_id,
                    "description": req_desc,
                    "status": req_status,
                    "evidence": ev_ref,
                }
            )
    else:
        # Default implicit requirement mapping based on observed test suite
        if passed_tests or failed_tests:
            for t in passed_tests:
                req_list.append(
                    {
                        "id": f"REQ-{t}",
                        "description": f"Verified behavior in {t}",
                        "status": "pass",
                        "evidence": t,
                    }
                )
            for t in failed_tests:
                req_list.append(
                    {
                        "id": f"REQ-{t}",
                        "description": f"Failed behavior in {t}",
                        "status": "fail",
                        "evidence": t,
                    }
                )

    findings_dict: dict[str, Any] = {
        "requirements": req_list,
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    # 3. Evaluate specification contract coverage via ContractEngine
    from the_judge.core.contract_engine import ContractEngine

    contract_engine = ContractEngine(task_spec=task_spec)
    contract_eval = contract_engine.evaluate_contract_coverage(ground_truth, findings_dict)
    ground_truth["contract_data"] = contract_eval

    # 4. Evaluate using score engine hard gates and trust profile engine
    eval_output = evaluate(findings_dict, ground_truth, previous_evidence=previous_evidence)

    # 4. Construct structured Findings for AI Agent consumption
    structured_findings: list[Finding] = []

    # Map failed tests to structured findings
    for idx, f_test in enumerate(failed_tests, 1):
        err_msg = test_suite.get("errors", {}).get(f_test, "Behavioral test execution failed.")
        structured_findings.append(
            Finding(
                id=f"BEH-{idx:03d}",
                category="behavior",
                severity="high",
                description=f"Behavioral test failed: {f_test}",
                property_name=f_test.replace("test_", ""),
                observed=err_msg[:200] if isinstance(err_msg, str) else str(err_msg),
                expected="Test passes with return value matching observable spec.",
                suggested_focus=f"Review state transitions and boundary logic tested in {f_test}.",
            )
        )

    # Map blocking issues (challenge missing, tampering, type errors)
    for idx, b_issue in enumerate(eval_output.get("blocking_issues", []), 1):
        if b_issue.startswith("Test suite failure:") and failed_tests:
            continue
        if "TAMPERING" in b_issue or "VERIFICATION DENIAL" in b_issue:
            cat = "security"
            sev = "blocking"
            focus = (
                "Ensure target code does not tamper with test collection or obscure verification."
            )
        elif "Type checker" in b_issue:
            cat = "type_check"
            sev = "high"
            focus = "Review type annotations and resolve static type checking errors."
        elif "REGRESSION" in b_issue:
            cat = "regression"
            sev = "blocking"
            focus = "Fix regression: restore functionality that previously passed."
        else:
            cat = "behavior"
            sev = "high"
            focus = "Resolve the blocking issue detected during evaluation."

        # Avoid duplicating failed test findings if already added
        if not any(f.description == b_issue for f in structured_findings):
            structured_findings.append(
                Finding(
                    id=f"GATE-{idx:03d}",
                    category=cat,
                    severity=sev,
                    description=b_issue,
                    suggested_focus=focus,
                )
            )

    # Map insufficient evidence notes as low/medium informational findings if ABSTAIN
    if eval_output.get("verdict") == "ABSTAIN":
        for idx, note in enumerate(eval_output.get("insufficient_evidence_notes", []), 1):
            structured_findings.append(
                Finding(
                    id=f"EVID-{idx:03d}",
                    category="collection",
                    severity="medium",
                    description=note,
                    suggested_focus="Provide independent behavioral property tests or implementation code that allows verification.",
                )
            )

    # 5. Compute Provenance & Hashes
    workspace_hash = _compute_workspace_hash(workspace_path)
    ev_cov = eval_output.get("evidence_coverage", {})
    provenance = {
        "workspace_path": workspace_path,
        "workspace_hash": workspace_hash,
        "judge_version": "v1.0.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_level": ev_cov.get("evidence_level", 0),
        "total_tests": ev_cov.get("total_tests", 0),
        "passed_tests": ev_cov.get("passed_tests", 0),
        "failed_tests": ev_cov.get("failed_tests", 0),
    }

    elapsed = time.time() - start_time

    # ev_cov was already extracted above; mutate it in-place to add spec coverage.
    ev_cov["specification_coverage"] = contract_eval

    return VerificationResult(
        decision=eval_output.get("verdict", "ABSTAIN"),
        numeric_score=eval_output.get("numeric_score", 0.0),
        trust_profile=ev_cov,
        findings=structured_findings,
        provenance=provenance,
        blocking_issues=eval_output.get("blocking_issues", []),
        insufficient_notes=eval_output.get("insufficient_evidence_notes", []),
        runtime_seconds=elapsed,
    )


def verify_workspace(workspace_dir: str) -> VerificationResult:
    """Convenience wrapper for verifying a workspace directory."""
    return verify(workspace=workspace_dir)


def improve(
    workspace: str,
    repair_func: Optional[Any] = None,
    max_rounds: int = 5,
    target_score: float = 90.0,
    task_spec: Optional[dict[str, Any]] = None,
    quality_evaluator: Optional[Any] = None,
    require_evidence_sufficiency: bool = True,
) -> dict[str, Any]:
    """Run the adversarial improvement loop on the target workspace.

    Philosophy
    ----------
    The agent that produces work cannot be trusted to judge its own work alone.
    This loop independently criticises the work, demands evidence, challenges
    assumptions, and drives improvements until the work is genuinely strong.

    Stopping requires ALL of:
      - quality score >= target_score
      - no unresolved CRITICAL or HIGH evidence-backed findings
      - no unresolved CONTRADICTED findings on material claims
      - evidence sufficiency is not "insufficient" (unless overridden)
      - judge decision is PASS

    A high score alone is NOT sufficient to stop.

    Loop: WORK -> EVIDENCE -> CRITIQUE -> IDENTIFY WEAKNESSES
          -> IMPROVE -> RE-EVALUATE -> REPEAT

    Args:
        workspace: Path to workspace directory or file.
        repair_func: Custom agent improvement callback. Defaults to built-in AutoImprover.
        max_rounds: Maximum improvement rounds (default: 5).
        target_score: Target quality score (0.0 to 100.0, default: 90.0).
        task_spec: Task specification contract (optional).
        quality_evaluator: Custom quality evaluation function (optional).
        require_evidence_sufficiency: If True (default), loop continues if evidence
            is "insufficient" even when score target is met.

    Returns:
        Dict containing multi-round history, audit trail, score progression,
        critique findings per round, and final verdict.
    """
    from the_judge.integrations.auto_improver import AutoImprover
    from the_judge.integrations.repair_loop import AgentRepairLoop

    if repair_func is None:
        improver = AutoImprover(workspace)

        def repair_func(ws, feedback):
            return improver.improve_workspace(feedback)

    loop = AgentRepairLoop(
        max_rounds=max_rounds,
        quality_threshold=target_score,
        quality_evaluator=quality_evaluator,
        require_evidence_sufficiency=require_evidence_sufficiency,
    )
    return loop.run_repair_loop(
        workspace=workspace,
        agent_repair_func=repair_func,
        task_spec=task_spec,
    )


def _compute_workspace_hash(workspace_path: str) -> str:
    """Compute SHA-256 digest of python files in workspace for round provenance."""
    hasher = hashlib.sha256()
    p = Path(workspace_path)
    if p.is_file():
        hasher.update(p.read_bytes())
    elif p.is_dir():
        for file_path in sorted(p.rglob("*.py")):
            hasher.update(file_path.read_bytes())
    else:
        hasher.update(workspace_path.encode("utf-8"))
    return hasher.hexdigest()
