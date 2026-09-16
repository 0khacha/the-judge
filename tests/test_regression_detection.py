import pytest
from judge.score_engine import evaluate


def test_regression_detection_triggers_hard_gate_fail() -> None:
    """Test that a previously passing test failing in current round triggers regression detection."""
    prev_evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 2,
            "passed_tests": ["test_feature_a", "test_feature_b"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    curr_evidence = {
        "test_suite": {
            "exit_code": 1,
            "total_tests": 2,
            "passed_tests": ["test_feature_a"],
            "failed_tests": ["test_feature_b"],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    findings = {
        "requirements": [
            {"id": "R1", "description": "Feature A", "status": "pass", "evidence": "test_feature_a"},
            {"id": "R2", "description": "Feature B", "status": "pass", "evidence": "test_feature_b"},
        ],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, curr_evidence, previous_evidence=prev_evidence)

    assert report["verdict"] == "FAIL"
    assert len(report["regressions"]) > 0
    assert any("test_feature_b" in r for r in report["regressions"])
    assert any("REGRESSION DETECTED" in b for b in report["blocking_issues"])


def test_no_false_regression_on_new_failures() -> None:
    """Test that a test failing in both rounds is not misflagged as a new regression."""
    prev_evidence = {
        "test_suite": {
            "exit_code": 1,
            "total_tests": 2,
            "passed_tests": ["test_feature_a"],
            "failed_tests": ["test_feature_b"],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    curr_evidence = {
        "test_suite": {
            "exit_code": 1,
            "total_tests": 2,
            "passed_tests": ["test_feature_a"],
            "failed_tests": ["test_feature_b"],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }

    findings = {
        "requirements": [],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }

    report = evaluate(findings, curr_evidence, previous_evidence=prev_evidence)

    assert len(report["regressions"]) == 0
