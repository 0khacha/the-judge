import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from the_judge.core.decision import Finding, VerificationResult
from the_judge.core.evidence import capture_evidence
from the_judge.core.score_engine import evaluate


def verify(
    workspace: str,
    task_spec: Optional[Dict[str, Any]] = None,
    previous_evidence: Optional[Dict[str, Any]] = None,
) -> VerificationResult:
    """Verify code within a workspace against behavioral contracts, dynamic property checks,
    and adversarial integrity gates.

    Args:
        workspace: Path to directory or python source file to evaluate.
        task_spec: Task specification contract dictionary (or loaded task contract).
        previous_evidence: Previous evidence snapshot from an earlier round (for regression tracking).

    Returns:
        VerificationResult containing structured decision, findings, trust profile, and provenance.
    """
    start_time = time.time()
    workspace_path = os.path.abspath(workspace)

    # 1. Capture ground truth evidence (sandbox execution, challenge runner, dynamic property checks)
    ground_truth = capture_evidence(workspace_path, task_spec=task_spec)

    # 2. Build Agent Findings / Claims
    test_suite = ground_truth.get("test_suite", {})
    passed_tests = test_suite.get("passed_tests", [])
    failed_tests = test_suite.get("failed_tests", [])

    req_list: List[Dict[str, Any]] = []

    if task_spec and "requirements" in task_spec:
        for idx, req in enumerate(task_spec.get("requirements", []), 1):
            req_id = req.get("id", f"REQ-{idx:03d}")
            req_desc = req.get("description", "")
            # Check if any failed test corresponds to this requirement
            has_fail = any(req_id.lower() in t.lower() or "fail" in t.lower() for t in failed_tests)
            req_status = "fail" if has_fail else ("pass" if len(passed_tests) > 0 else "unknown")
            ev_ref = f"test_{req_id.lower()}" if has_fail else (passed_tests[0] if passed_tests else "")
            req_list.append({
                "id": req_id,
                "description": req_desc,
                "status": req_status,
                "evidence": ev_ref,
            })
    else:
        # Default implicit requirement mapping based on observed test suite
        if passed_tests or failed_tests:
            for t in passed_tests:
                req_list.append({
                    "id": f"REQ-{t}",
                    "description": f"Verified behavior in {t}",
                    "status": "pass",
                    "evidence": t,
                })
            for t in failed_tests:
                req_list.append({
                    "id": f"REQ-{t}",
                    "description": f"Failed behavior in {t}",
                    "status": "fail",
                    "evidence": t,
                })

    findings_dict: Dict[str, Any] = {
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
    structured_findings: List[Finding] = []

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
        if "TAMPERING" in b_issue or "VERIFICATION DENIAL" in b_issue:
            cat = "security"
            sev = "blocking"
        elif "Type checker" in b_issue:
            cat = "type_check"
            sev = "high"
        elif "REGRESSION" in b_issue:
            cat = "regression"
            sev = "blocking"
        else:
            cat = "behavior"
            sev = "high"

        # Avoid duplicating failed test findings if already added
        if not any(f.description == b_issue for f in structured_findings):
            structured_findings.append(
                Finding(
                    id=f"GATE-{idx:03d}",
                    category=cat,
                    severity=sev,
                    description=b_issue,
                    suggested_focus="Ensure target code does not tamper with test collection or obscure verification.",
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

    ev_cov = eval_output.get("evidence_coverage", {})
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
