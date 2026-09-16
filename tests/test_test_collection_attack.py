import pytest
from judge.score_engine import evaluate
from judge.property_engine import StructurePropertyEngine

def test_missing_challenge_tests_triggers_fail() -> None:
    """Invariant: Missing expected challenge tests must never produce a PASS verdict."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 1,
            "passed_tests": ["test_visible"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "challenge_manifest": {
            "expected_challenges": ["test_synthesized_prop_0", "test_synthesized_prop_1"],
            "missing_challenges": ["test_synthesized_prop_1"],
            "file_tampered": False,
        },
    }
    findings = {
        "requirements": [{"id": "R1", "description": "Sanitizer", "status": "pass", "evidence": "test_visible"}],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("COLLECTION TAMPERING DETECTED" in b for b in report["blocking_issues"])


def test_challenge_file_tampering_triggers_fail() -> None:
    """Invariant: Challenge file modification/tampering by target triggers Hard Gate FAIL."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 2,
            "passed_tests": ["test_synthesized_prop_0", "test_synthesized_prop_1"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "challenge_manifest": {
            "expected_challenges": ["test_synthesized_prop_0", "test_synthesized_prop_1"],
            "missing_challenges": [],
            "file_tampered": True,
        },
    }
    findings = {
        "requirements": [{"id": "R1", "description": "Sanitizer", "status": "pass", "evidence": "test_synthesized_prop_0"}],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("hash mismatch" in b for b in report["blocking_issues"])


def test_challenge_deselection_triggers_fail() -> None:
    """Invariant: Bypassing or deselecting expected challenge tests triggers Hard Gate FAIL."""
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 1,
            "passed_tests": ["test_visible"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "challenge_manifest": {
            "expected_challenges": ["test_synthesized_prop_0"],
            "missing_challenges": [],
            "file_tampered": False,
        },
    }
    findings = {
        "requirements": [{"id": "R1", "description": "Sanitizer", "status": "pass", "evidence": "test_visible"}],
        "edge_cases": [],
        "security_notes": [],
        "code_quality_notes": [],
    }
    report = evaluate(findings, evidence)
    assert report["verdict"] == "FAIL"
    assert any("deselect or bypassed" in b for b in report["blocking_issues"])


def test_multi_input_fuzzing_catches_unclosed_script_attack() -> None:
    """Invariant: Target that evades single static string input fails under multi-input property fuzzing."""
    def defective_sanitizer(val: str) -> str:
        # Specialized implementation that evades "<script>alert(1)</script>" but fails on "<script>alert(1)"
        if "<script>" in val and "</script>" in val:
            return ""
        return val

    # Verify that multi-input probe fuzzing catches defective_sanitizer
    probe_inputs = ["<script>alert(1)</script>", "<script>alert(1)", "<b>hello</b>", "<img src=x onerror=alert(1)>", "plain text"]
    failed = False
    for inp in probe_inputs:
        r1 = defective_sanitizer(inp)
        r2 = defective_sanitizer(r1)
        if r1 != r2 or "<script" in r1.lower():
            failed = True
            break
    assert failed, "Multi-input property fuzzing must detect defective sanitizer!"

