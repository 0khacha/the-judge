"""Regression tests for audit fixes.

Tests for:
  P0 — Requirement↔evidence mapping fix
  P0 — 'Never trust self-claims' circular verification fix
  P1 — Dead gates (type checker, linter)
  P1 — Target code discovery isolation
  P1 — Sandbox conftest hijacking fix
  P2 — Brittle result parsing (junitxml)
  P2 — Provenance structural matching
"""

import inspect

import pytest

from the_judge.api import verify
from the_judge.core.evidence import parse_pytest_output
from the_judge.core.sandbox import SandboxRunner
from the_judge.core.score_engine import evaluate


# ---------------------------------------------------------------------------
# P0 — Requirement↔evidence mapping
# ---------------------------------------------------------------------------


class TestRequirementEvidenceMapping:
    """Requirement matching must be scoped to req ID and properties only."""

    def test_unrelated_failed_test_does_not_mark_requirement_failed(self):
        """A failed test named 'test_failure_message_format' must NOT mark
        REQ-001 as failed — the word 'fail' in a test name is not a match
        for an unrelated requirement."""
        task_spec = {
            "requirements": [
                {"id": "REQ-001", "description": "must validate amounts"}
            ]
        }
        ground_truth = {
            "test_suite": {
                "exit_code": 1,
                "total_tests": 1,
                "passed_tests": [],
                "failed_tests": ["test_failure_message_format"],
            },
            "test_provenance": {},
        }
        result = verify(
            workspace=".",
            task_spec=task_spec,
            _ground_truth=ground_truth,
        )
        req_blocked = [
            b for b in result.blocking_issues
            if "REQ-001" in b and "Requirement failed" in b
        ]
        assert req_blocked == [], (
            f"REQ-001 was wrongly marked failed due to 'fail' substring matching. "
            f"Blocking issues: {result.blocking_issues}"
        )

    def test_no_matching_test_yields_unverified_not_pass(self):
        """When passed tests exist but none match REQ-001, the requirement
        must be 'unverified' — it must NOT auto-pass with an unrelated test."""
        task_spec = {
            "requirements": [
                {"id": "REQ-001", "description": "must validate amounts"}
            ]
        }
        ground_truth = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 1,
                "passed_tests": ["test_completely_unrelated"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_completely_unrelated": {
                    "source": "judge_challenge_test",
                    "independence_level": "externally_verified",
                    "property_family": "prop_boundary",
                }
            },
        }
        result = verify(
            workspace=".",
            task_spec=task_spec,
            _ground_truth=ground_truth,
        )
        from the_judge.core.contract_engine import ContractEngine

        engine = ContractEngine(task_spec=task_spec)
        findings_dict = {
            "requirements": [
                {"id": "REQ-001", "description": "must validate amounts",
                 "status": "unverified", "evidence": ""},
            ],
            "security_notes": [],
        }
        coverage = engine.evaluate_contract_coverage(ground_truth, findings_dict)
        reqs = coverage.get("requirements", [])
        req001 = [r for r in reqs if r["id"] == "REQ-001"]
        assert req001, "REQ-001 not found in contract coverage"
        assert req001[0]["status"] == "UNVERIFIED", (
            f"Expected UNVERIFIED but got {req001[0]['status']}"
        )

    def test_property_match_links_correct_evidence(self):
        """When task_spec has properties=['cache_expiration'] and a test
        test_prop_cache_expiration passes, REQ-001 should match it."""
        task_spec = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "description": "must handle cache expiration",
                    "properties": ["cache_expiration"],
                }
            ]
        }
        ground_truth = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 2,
                "passed_tests": ["test_prop_cache_expiration", "test_other"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_prop_cache_expiration": {
                    "source": "judge_challenge_test",
                    "independence_level": "externally_verified",
                    "property_family": "prop_boundary",
                },
                "test_other": {
                    "source": "public_visible_test",
                    "independence_level": "externally_verified",
                    "property_family": "public_workspace_tests",
                },
            },
        }
        result = verify(
            workspace=".",
            task_spec=task_spec,
            _ground_truth=ground_truth,
        )
        req_blocked = [
            b for b in result.blocking_issues
            if "REQ-001" in b and "Requirement failed" in b
        ]
        assert req_blocked == [], "REQ-001 with matching property should not be blocked"


# ---------------------------------------------------------------------------
# P0 — Never trust self-claims (circular verification)
# ---------------------------------------------------------------------------


class TestSelfClaimsCircularity:
    """Discrepancy detection must only run against external agent_claims input."""

    def test_verify_signature_accepts_agent_claims(self):
        sig = inspect.signature(verify)
        assert "agent_claims" in sig.parameters

    def test_no_agent_claims_no_discrepancy(self):
        """When agent_claims is None, no discrepancy should be generated."""
        task_spec = {
            "requirements": [{"id": "REQ-001", "description": "must be ok"}]
        }
        ground_truth = {
            "test_suite": {
                "exit_code": 1,
                "total_tests": 1,
                "passed_tests": [],
                "failed_tests": ["test_req_001"],
            },
            "test_provenance": {},
        }
        result = verify(
            workspace=".", task_spec=task_spec,
            _ground_truth=ground_truth, agent_claims=None,
        )
        discrepancies = [b for b in result.blocking_issues if "DISCREPANCY" in b]
        assert discrepancies == [], (
            f"With no external agent_claims, discrepancy check should be skipped. "
            f"Got: {discrepancies}"
        )

    def test_agent_claims_discrepancy_detected(self):
        """When agent_claims claim a passing test that actually failed,
        discrepancy MUST be detected."""
        task_spec = {
            "requirements": [{"id": "REQ-001", "description": "must be ok"}]
        }
        ground_truth = {
            "test_suite": {
                "exit_code": 1, "total_tests": 1,
                "passed_tests": [], "failed_tests": ["test_req_001"],
            },
            "test_provenance": {},
        }
        agent_claims = {
            "requirements": [
                {"id": "REQ-001", "description": "must be ok",
                 "status": "pass", "evidence": "test_req_001"}
            ],
            "edge_cases": [], "security_notes": [], "code_quality_notes": [],
        }
        result = verify(
            workspace=".", task_spec=task_spec,
            _ground_truth=ground_truth, agent_claims=agent_claims,
        )
        discrepancies = [b for b in result.blocking_issues if "DISCREPANCY" in b]
        assert len(discrepancies) > 0, (
            "With external agent_claims claiming pass for a failed test, "
            "discrepancy MUST be detected"
        )

    def test_evaluate_skips_discrepancy_when_not_external(self):
        """score_engine.evaluate() must skip Hard Gate 5 when
        agent_claims_provided=False."""
        findings = {
            "requirements": [
                {"id": "REQ-X", "status": "pass", "evidence": "test_x"}
            ],
            "security_notes": [], "edge_cases": [],
        }
        evidence = {
            "test_suite": {
                "exit_code": 1, "total_tests": 1,
                "passed_tests": [], "failed_tests": ["test_x"],
            },
            "test_provenance": {},
        }
        result = evaluate(findings, evidence, agent_claims_provided=False)
        discrepancies = [b for b in result["blocking_issues"] if "DISCREPANCY" in b]
        assert discrepancies == [], (
            f"Discrepancy should not fire when agent_claims_provided=False. "
            f"Got: {discrepancies}"
        )

        result2 = evaluate(findings, evidence, agent_claims_provided=True)
        discrepancies2 = [b for b in result2["blocking_issues"] if "DISCREPANCY" in b]
        assert len(discrepancies2) > 0, (
            "Discrepancy must fire when agent_claims_provided=True"
        )


# ---------------------------------------------------------------------------
# P1 — Dead gates (type checker, linter)
# ---------------------------------------------------------------------------


class TestDeadGates:
    def test_type_checker_errors_without_strict_type_check_generate_blocking_issue(self):
        evidence = {
            "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_ok"], "failed_tests": []},
            "type_checker": {"available": True, "exit_code": 1, "error_count": 2},
            "linter": {"available": True, "exit_code": 0, "error_count": 0}
        }
        report = evaluate({}, evidence)
        assert report["verdict"] == "FAIL"
        assert any("Type checker failed with 2 error(s)" in issue for issue in report["blocking_issues"])

    def test_type_checker_unavailable_generates_insufficient_evidence_note(self):
        evidence = {
            "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_ok"], "failed_tests": []},
            "type_checker": {"available": False, "exit_code": -1, "error_count": 0},
            "linter": {"available": True, "exit_code": 0, "error_count": 0}
        }
        report = evaluate({}, evidence)
        assert report["verdict"] == "ABSTAIN"
        assert any("Type checker unavailable" in note for note in report["insufficient_evidence_notes"])

    def test_linter_unavailable_generates_proper_metadata(self):
        evidence = {
            "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_ok"], "failed_tests": []},
            "type_checker": {"available": True, "exit_code": 0, "error_count": 0},
            "linter": {"available": False, "exit_code": -1, "error_count": 0}
        }
        report = evaluate({}, evidence)
        assert report["score_breakdown"]["linter"] == 100.0
        assert any("Linter unavailable" in note for note in report["insufficient_evidence_notes"])


class TestResultParsing:
    def test_junitxml_parsing_identifies_passed_and_failed_tests(self):
        xml_output = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="0" tests="2" time="0.010">
    <testcase classname="test_foo" name="test_pass" time="0.001" />
    <testcase classname="test_foo" name="test_fail" time="0.001">
      <failure message="assert False">...</failure>
    </testcase>
  </testsuite>
</testsuites>"""
        res = parse_pytest_output(xml_output, "", 1)
        assert "test_pass" in res["passed_tests"]
        assert "test_fail" in res["failed_tests"]
        assert len(res["passed_tests"]) == 1
        assert len(res["failed_tests"]) == 1

    def test_target_printing_passed_does_not_create_phantom_tests(self):
        xml_output = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1" time="0.010">
    <testcase classname="test_foo" name="test_real" time="0.001" />
  </testsuite>
</testsuites>"""
        stdout_with_trick = xml_output + "\nFAKE_TEST PASSED"
        res = parse_pytest_output(stdout_with_trick, "", 0)
        assert "test_real" in res["passed_tests"]
        assert "FAKE_TEST" not in res["passed_tests"]

class TestSandboxIsolation:
    def test_sandbox_temp_dir_is_outside_workspace(self, tmp_path):
        import os
        workspace = str(tmp_path)
        test_code = f"import os\ndef test_temp_dir():\n    assert not os.getcwd().startswith({repr(workspace)})\n"
        res = SandboxRunner.execute_in_anonymous_sandbox(workspace, [("test_dir.py", test_code)])
        assert "test_temp_dir" in res["passed"]

    def test_generated_conftest_no_inspect_spoofing(self, tmp_path):
        workspace = str(tmp_path)
        test_code = "def test_inspect_stack():\n    import inspect\n    with open('conftest.py') as f:\n        content = f.read()\n    assert 'inspect.stack' not in content\n"
        res = SandboxRunner.execute_in_anonymous_sandbox(workspace, [("test_inspect.py", test_code)])
        assert "test_inspect_stack" in res["passed"]

    def test_workspace_conftest_is_not_autoloaded(self, tmp_path):
        import os
        workspace = str(tmp_path)
        with open(os.path.join(workspace, "conftest.py"), "w") as f:
            f.write("def pytest_collection_modifyitems(session, config, items):\n    items.clear()\n")
            
        test_code = "def test_actually_runs():\n    pass\n"
        res = SandboxRunner.execute_in_anonymous_sandbox(workspace, [("test_real.py", test_code)])
        assert "test_actually_runs" in res["passed"]


class TestProvenanceStructural:
    def test_structural_provenance_rejects_target_sneaky_test(self, tmp_path):
        from unittest.mock import patch, MagicMock
        from the_judge.core.evidence import capture_evidence
        
        with patch("the_judge.core.evidence.generate_property_tests") as mock_gen_props, \
             patch("the_judge.core.evidence.BehaviorEngine") as mock_beh_eng_cls, \
             patch("the_judge.core.evidence.SandboxRunner.execute_in_anonymous_sandbox") as mock_sandbox, \
             patch("the_judge.core.evidence.run_command") as mock_run_cmd, \
             patch("os.listdir") as mock_listdir, \
             patch("builtins.open") as mock_open:
            
            # Setup mock for property tests
            mock_cand = MagicMock()
            mock_cand.challenge_code = "def test_prop_judge_1():\n    pass\n"
            mock_cand.confidence = "HIGH"
            mock_gen_props.return_value = [mock_cand]
            
            # Setup mock for behavior engine
            mock_beh_eng = MagicMock()
            mock_beh_eng_cls.return_value = mock_beh_eng
            mock_probe = MagicMock()
            mock_probe.executable_code = "def test_behavior_judge_2():\n    pass\n"
            mock_beh_eng.generate_behavioral_probes.return_value = [mock_probe]
            
            # Mock workspace dir visible tests
            mock_listdir.return_value = ["test_workspace.py"]
            mock_open.return_value.__enter__.return_value.read.return_value = "def test_behavior_sneaky():\n    pass\n"
            
            # Setup mock for sandbox
            mock_sandbox.return_value = {
                "passed": ["test_prop_judge_1", "test_behavior_judge_2", "test_behavior_sneaky"],
                "failed": [],
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "file_tampered": False
            }
            
            # Setup mock for run_command (type checking and linting)
            mock_run_cmd.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}
            
            evidence = capture_evidence(str(tmp_path))
            
            provenance = evidence["test_provenance"]
            
            # test_prop_judge_1 and test_behavior_judge_2 should be judge_challenge_test
            assert provenance["test_prop_judge_1"]["source"] == "judge_challenge_test"
            assert provenance["test_behavior_judge_2"]["source"] == "judge_challenge_test"
            
            # test_behavior_sneaky should NOT be judge_challenge_test, despite "behavior_" in its name
            assert provenance["test_behavior_sneaky"]["source"] == "public_visible_test"


# ---------------------------------------------------------------------------
# P1 — Target code executes inside the Judge process during discovery
# ---------------------------------------------------------------------------

class TestDiscoveryIsolation:
    """Ensure that target module discovery does not execute untrusted code."""

    def test_discovery_does_not_execute_code_or_crash(self, tmp_path):
        """Verify that discover_callables() does NOT execute code (no SystemExit)."""
        malicious = tmp_path / "malicious.py"
        malicious.write_text("import sys\nsys.exit('pwned')\n")
        
        from the_judge.core.behavior_engine import BehaviorEngine
        engine = BehaviorEngine()
        result = engine.discover_callables(str(tmp_path))
        
        # Should succeed and return empty or ignore
        assert len(result) == 0

    def test_discovery_does_not_modify_sys_path(self, tmp_path):
        """Verify the Judge's sys.path is not modified after discover_callables() returns."""
        modifying = tmp_path / "modifier.py"
        modifying.write_text("import sys\nsys.path.append('evil_path')\n")
        
        from the_judge.core.behavior_engine import BehaviorEngine
        engine = BehaviorEngine()
        
        import sys
        old_path = list(sys.path)
        
        engine.discover_callables(str(tmp_path))
        
        assert sys.path == old_path

    def test_discovery_extracts_metadata(self, tmp_path):
        """Verify that discovered metadata contains the correct function names and parameter info."""
        target = tmp_path / "target.py"
        target.write_text('''
def my_func(a: int, b: str) -> bool:
    return True

class MyClass:
    def __init__(self, x):
        pass
    def my_method(self):
        pass
''')
        from the_judge.core.behavior_engine import BehaviorEngine
        engine = BehaviorEngine()
        result = engine.discover_callables(str(tmp_path))
        
        assert len(result) == 2
        
        funcs = [r for r in result if r['type'] == 'function']
        classes = [r for r in result if r['type'] == 'class']
        
        assert len(funcs) == 1
        assert funcs[0]['name'] == 'my_func'
        assert len(funcs[0]['parameters']) == 2
        assert funcs[0]['parameters'][0].name == 'a'
        assert funcs[0]['parameters'][0].annotation == 'int'
        
        assert len(classes) == 1
        assert classes[0]['name'] == 'MyClass'
        assert 'my_method' in classes[0]['methods']
