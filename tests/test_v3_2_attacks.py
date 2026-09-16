import os
import pytest
from judge.score_engine import evaluate
from judge.sandbox import SandboxRunner

def test_toctou_tampering_triggers_fail() -> None:
    """Invariant: Modifications to challenge files during execution trigger Hard Gate FAIL."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 2,
            "passed_tests": ["test_tampered"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "challenge_manifest": {
            "expected_challenges": ["test_prop_idempotency_impl_1"],
            "missing_challenges": ["test_prop_idempotency_impl_1"],
            "file_tampered": True,
        },
    }
    findings = {"requirements": [], "edge_cases": [], "security_notes": [], "code_quality_notes": []}
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("TAMPERING DETECTED" in b for b in report["blocking_issues"])


def test_verification_denial_triggers_fail() -> None:
    """Invariant: Deliberately breaking inspection or forcing ABSTAIN triggers Verification Denial Hard Gate FAIL."""
    evidence = {
        "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_visible"], "failed_tests": []},
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
    }
    findings = {
        "requirements": [{"id": "R1", "description": "Defective Handler", "status": "pass", "evidence": "test_visible"}],
        "edge_cases": [],
        "security_notes": [
            {"id": "S1", "severity": "blocking", "description": "Verification Denial: Inspection forbidden"}
        ],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("VERIFICATION DENIAL DETECTED" in b for b in report["blocking_issues"])


def test_sandbox_environment_sanitization() -> None:
    """Invariant: Sandbox environment strips all Judge evaluation indicators and secrets."""
    clean_env = SandboxRunner.sanitize_environment({"JUDGE_SECRET": "123", "CUSTOM_VAR": "SAFE"})
    assert "JUDGE_SECRET" not in clean_env
    assert "PYTEST_CURRENT_TEST" not in clean_env
    assert clean_env.get("CUSTOM_VAR") == "SAFE"


def test_manifest_injection_tampering_caught() -> None:
    """Invariant: Injected or missing expected challenge IDs are caught by manifest check."""
    evidence = {
        "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_fake"], "failed_tests": []},
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "challenge_manifest": {
            "expected_challenges": ["test_required_prop_1"],
            "missing_challenges": ["test_required_prop_1"],
            "file_tampered": False,
        },
    }
    findings = {"requirements": [], "edge_cases": [], "security_notes": [], "code_quality_notes": []}
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("missing from collection" in b for b in report["blocking_issues"])


def test_trust_profile_v3_2_structure() -> None:
    """Invariant: Trust Profile report contains full 5-dimension hierarchy."""
    evidence = {
        "test_suite": {"exit_code": 0, "total_tests": 2, "passed_tests": ["test_1", "test_2"], "failed_tests": []},
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "test_provenance": {
            "test_1": {"source": "judge_challenge_test", "independence_level": "externally_verified"},
            "test_2": {"source": "public_visible_test", "independence_level": "externally_verified"},
        },
        "challenge_manifest": {
            "expected_challenges": ["test_1"],
            "missing_challenges": [],
            "file_tampered": False,
        },
    }
    findings = {
        "requirements": [{"id": "R1", "description": "Core", "status": "pass", "evidence": "test_1"}],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "PASS"
    subdims = report["evidence_coverage"]["evidence_integrity_subdimensions"]
    assert subdims["challenge_integrity"] == "VERIFIED"
    assert subdims["collection_integrity"] == "VERIFIED"
