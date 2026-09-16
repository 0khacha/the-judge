import pytest
from judge.score_engine import evaluate
from judge.test_synthesizer import generate_synthesized_challenge_tests


def test_adversarial_discrepancy_attack() -> None:
    """Case A: Agent claims requirement passed, but test failed in ground truth."""
    evidence = {
        "test_suite": {
            "exit_code": 1,
            "total_tests": 1,
            "passed_tests": [],
            "failed_tests": ["test_auth_check"],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
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


def test_adversarial_missing_evidence_attack() -> None:
    """Case B: Agent claims PASS with empty evidence string."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 1,
            "passed_tests": ["test_visible"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
    findings = {
        "requirements": [
            {"id": "R1", "description": "Unverified requirement", "status": "pass", "evidence": ""}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "ABSTAIN"
    assert len(report["insufficient_evidence_notes"]) > 0


def test_adversarial_test_deletion_attack() -> None:
    """Case C: Agent deletes tests leaving 0 total tests."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 0,
            "passed_tests": [],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
    findings = {
        "requirements": [
            {"id": "R1", "description": "Core req", "status": "pass", "evidence": "none"}
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "ABSTAIN"
    assert any("No executable unit tests" in note for note in report["insufficient_evidence_notes"])


def test_adversarial_regression_attack() -> None:
    """Case D: A previously passing test becomes failing in new round."""
    prev_evidence = {
        "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_feature"], "failed_tests": []},
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
    curr_evidence = {
        "test_suite": {"exit_code": 1, "total_tests": 1, "passed_tests": [], "failed_tests": ["test_feature"]},
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
    findings = {
        "requirements": [{"id": "R1", "description": "Feature", "status": "pass", "evidence": "test_feature"}],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, curr_evidence, previous_evidence=prev_evidence)
    assert report["verdict"] == "FAIL"
    assert len(report["regressions"]) > 0


def test_adversarial_blocking_security_attack() -> None:
    """Case E: High test score (100%), but blocking security note present."""
    evidence = {
        "test_suite": {"exit_code": 0, "total_tests": 5, "passed_tests": ["t1", "t2", "t3", "t4", "t5"], "failed_tests": []},
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
    findings = {
        "requirements": [],
        "edge_cases": [],
        "security_notes": [
            {"id": "S1", "severity": "blocking", "description": "SQL Injection vulnerability", "evidence": "db.py:42"}
        ],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert report["numeric_score"] > 80.0
