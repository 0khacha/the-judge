import pytest
from judge.score_engine import evaluate


def test_discrepancy_detection_hard_gate() -> None:
    """Test that claiming PASS on a failing test triggers a discrepancy hard gate FAIL."""
    evidence = {
        "test_suite": {
            "exit_code": 1,
            "total_tests": 1,
            "passed_tests": [],
            "failed_tests": ["test_token_expiry"],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    findings = {
        "requirements": [],
        "edge_cases": [
            {
                "id": "E1",
                "description": "Token expiry check",
                "status": "pass",
                "evidence": "test_token_expiry",
            }
        ],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)

    assert report["verdict"] == "FAIL"
    assert len(report["discrepancies"]) == 1
    assert "E1" in report["discrepancies"][0]


def test_blocking_security_note_hard_gate() -> None:
    """Test that a blocking security note forces FAIL despite 100% test pass."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 5,
            "passed_tests": ["t1", "t2", "t3", "t4", "t5"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    findings = {
        "requirements": [],
        "edge_cases": [],
        "security_notes": [
            {
                "id": "S1",
                "severity": "blocking",
                "description": "Hardcoded secret key in repository",
                "evidence": "config.py:10",
            }
        ],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)

    assert report["verdict"] == "FAIL"
    assert report["numeric_score"] > 80.0  # High score but FAIL verdict!
    assert any("Blocking security note" in b for b in report["blocking_issues"])


def test_clean_pass_verdict() -> None:
    """Test that clean passing evidence and findings yield PASS verdict."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 2,
            "passed_tests": ["t1", "t2"],
            "failed_tests": [],
        },
        "test_provenance": {
            "t1": {"source": "judge_challenge_test", "independence_level": "judge_generated"},
            "t2": {"source": "public_visible_test", "independence_level": "externally_verified"},
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    findings = {
        "requirements": [
            {"id": "R1", "description": "Req 1", "status": "pass", "evidence": "t1"},
            {"id": "R2", "description": "Req 2", "status": "pass", "evidence": "t2"},
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, evidence)

    assert report["verdict"] == "PASS"
    assert report["numeric_score"] == 100.0
    assert len(report["blocking_issues"]) == 0
