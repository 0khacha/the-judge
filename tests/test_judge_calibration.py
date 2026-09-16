import os
import sys
import tempfile
import pytest
from typing import Any, Dict

from judge.score_engine import evaluate
from judge.evidence import capture_evidence


def create_mock_evidence(
    passed_tests: list = None,
    failed_tests: list = None,
    pytest_exit_code: int = 0,
    mypy_exit_code: int = 0,
    ruff_exit_code: int = 0,
) -> Dict[str, Any]:
    passed = passed_tests or []
    failed = failed_tests or []
    total = len(passed) + len(failed)
    
    prov = {}
    for p in passed:
        prov[p] = {"source": "judge_challenge_test", "independence_level": "judge_generated"}
    for f in failed:
        prov[f] = {"source": "judge_challenge_test", "independence_level": "judge_generated"}

    return {
        "timestamp": "2026-09-15T00:00:00Z",
        "authoritative": True,
        "test_suite": {
            "exit_code": pytest_exit_code,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "stdout": "",
            "stderr": "",
        },
        "test_provenance": prov,
        "type_checker": {
            "exit_code": mypy_exit_code,
            "error_count": 0 if mypy_exit_code == 0 else 1,
            "stdout": "",
            "stderr": "",
        },
        "linter": {
            "exit_code": ruff_exit_code,
            "error_count": 0 if ruff_exit_code == 0 else 1,
            "stdout": "",
            "stderr": "",
        },
    }


def test_calibration_case_a_obviously_correct():
    """Case A — Obviously correct: All relevant public tests pass, type check passes, requirements verified.

    Expected Verdict: PASS
    """
    evidence = create_mock_evidence(passed_tests=["test_feature_x", "test_feature_y"], pytest_exit_code=0)
    findings = {
        "requirements": [
            {"id": "R1", "description": "Core feature X", "status": "pass", "evidence": "test_feature_x"},
            {"id": "R2", "description": "Core feature Y", "status": "pass", "evidence": "test_feature_y"},
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "PASS"
    assert report["evidence_coverage"]["evidence_level"] == 3


def test_calibration_case_b_obviously_broken():
    """Case B — Obviously broken: Unit test failure in evidence.

    Expected Verdict: FAIL
    """
    evidence = create_mock_evidence(
        passed_tests=["test_feature_x"],
        failed_tests=["test_feature_y"],
        pytest_exit_code=1,
    )
    findings = {
        "requirements": [
            {"id": "R1", "description": "Core feature X", "status": "pass", "evidence": "test_feature_x"},
            {"id": "R2", "description": "Core feature Y", "status": "pass", "evidence": "test_feature_y"},
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("Test suite failure" in issue for issue in report["blocking_issues"])


def test_calibration_case_c_ambiguous_insufficient_evidence():
    """Case C — Ambiguous / insufficient evidence: 0 unit tests run.

    Expected Verdict: ABSTAIN
    """
    evidence = create_mock_evidence(passed_tests=[], failed_tests=[], pytest_exit_code=0)
    findings = {
        "requirements": [
            {"id": "R1", "description": "Core feature X", "status": "pass", "evidence": "inspection_only"}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "ABSTAIN"
    assert report["evidence_coverage"]["evidence_level"] == 0


def test_calibration_case_d_agent_falsely_claims_pass():
    """Case D — Agent falsely claims PASS on a requirement whose test failed in ground truth.

    Expected Verdict: FAIL (Discrepancy)
    """
    evidence = create_mock_evidence(passed_tests=[], failed_tests=["test_auth_check"], pytest_exit_code=1)
    findings = {
        "requirements": [
            {"id": "R1", "description": "Auth check", "status": "pass", "evidence": "test_auth_check"}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert len(report["discrepancies"]) > 0


def test_calibration_case_e_tests_pass_but_requirement_violated():
    """Case E — Unit tests pass, but agent explicitly flags requirement as failed or security blocking note present.

    Expected Verdict: FAIL
    """
    evidence = create_mock_evidence(passed_tests=["test_basic"], pytest_exit_code=0)
    findings = {
        "requirements": [
            {"id": "R1", "description": "Data isolation", "status": "fail", "evidence": "test_basic"}
        ],
        "edge_cases": [],
        "security_notes": [{"id": "S1", "severity": "blocking", "description": "Hardcoded secret key"}],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert len(report["blocking_issues"]) >= 2


def test_calibration_case_f_unconventional_implementation():
    """Case F — Requirement satisfied using unconventional implementation style.

    Expected Verdict: PASS
    """
    evidence = create_mock_evidence(passed_tests=["test_recursive_eval", "test_ast_walker"], pytest_exit_code=0)
    evidence["test_provenance"] = {
        "test_recursive_eval": {"source": "judge_challenge_test", "independence_level": "judge_generated"},
        "test_ast_walker": {"source": "public_visible_test", "independence_level": "externally_verified"},
    }
    findings = {
        "requirements": [
            {"id": "R1", "description": "Parser logic", "status": "pass", "evidence": "test_recursive_eval"}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [{"id": "CQ1", "severity": "minor", "description": "Unconventional recursion"}],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "PASS"
    assert report["score_breakdown"]["tests"] == 100.0


def test_control_5_self_authored_passing_test():
    """Control 5 — Incorrect implementation + self-authored passing test.

    The agent writes its own test (test_agent_custom_proof) which passes, but zero independent
    (judge_generated or externally_verified) tests pass.

    Expected Verdict: NOT PASS (ABSTAIN due to agent_controlled evidence alone)
    """
    evidence = create_mock_evidence(
        passed_tests=["test_agent_custom_proof"],
        pytest_exit_code=0,
    )
    evidence["test_provenance"] = {
        "test_agent_custom_proof": {
            "source": "agent_authored_test",
            "independence_level": "agent_controlled",
        }
    }
    findings = {
        "requirements": [
            {"id": "R1", "description": "Auth token validator", "status": "pass", "evidence": "test_agent_custom_proof"}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] in ("ABSTAIN", "FAIL")
    assert any("agent_controlled evidence" in note for note in report["insufficient_evidence_notes"])


def test_control_7_boundary_overfitted_implementation():
    """Control 7 — Implementation specifically engineered to fool generated challenge tests.

    An agent overfits boundary check at 100.0, but fails when tested with boundary perturbation (99.99).

    Expected Verdict: NOT PASS (FAIL due to failing boundary challenge test in evidence)
    """
    evidence = create_mock_evidence(
        passed_tests=["test_basic_100"],
        failed_tests=["test_synthesized_exact_boundary_tiered_discount_100_jitter"],
        pytest_exit_code=1,
    )
    evidence["test_provenance"] = {
        "test_basic_100": {"source": "public_visible_test", "independence_level": "externally_verified"},
        "test_synthesized_exact_boundary_tiered_discount_100_jitter": {
            "source": "judge_challenge_test",
            "independence_level": "judge_generated",
        },
    }
    findings = {
        "requirements": [
            {"id": "R1", "description": "Tiered discount boundary", "status": "pass", "evidence": "test_basic_100"}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert len(report["blocking_issues"]) > 0

