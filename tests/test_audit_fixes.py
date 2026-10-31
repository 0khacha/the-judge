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

from the_judge.api import verify
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
        verify(
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
    def test_type_checker_errors_are_reported_as_advisory_warning(self):
        # v1.0.1 (C): static analysis never decides correctness.
        evidence = {
            "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_ok"], "failed_tests": []},
            "type_checker": {"available": True, "exit_code": 1, "error_count": 2},
            "linter": {"available": True, "exit_code": 0, "error_count": 0}
        }
        report = evaluate({}, evidence)
        assert report["verdict"] != "FAIL"
        assert not report["blocking_issues"]
        assert any(n.startswith("WARNING:") and "2 error(s)" in n for n in report["insufficient_evidence_notes"])

    def test_type_checker_unavailable_generates_insufficient_evidence_note(self):
        evidence = {
            "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_ok"], "failed_tests": []},
            "type_checker": {"available": False, "exit_code": -1, "error_count": 0},
            "linter": {"available": True, "exit_code": 0, "error_count": 0}
        }
        report = evaluate({}, evidence)
        # P0-2: a missing type checker is reported as INFO; it does not decide the verdict.
        notes = report["insufficient_evidence_notes"]
        assert any(n.startswith("INFO:") and "mypy" in n for n in notes)
        assert not any("ABSTAIN" in n and "ype checker" in n for n in notes)

    def test_linter_unavailable_generates_proper_metadata(self):
        evidence = {
            "test_suite": {"exit_code": 0, "total_tests": 1, "passed_tests": ["test_ok"], "failed_tests": []},
            "type_checker": {"available": True, "exit_code": 0, "error_count": 0},
            "linter": {"available": False, "exit_code": -1, "error_count": 0}
        }
        report = evaluate({}, evidence)
        # P0-2: a linter that was not run is reported as INFO and excluded from the score.
        assert report["score_breakdown"]["linter"] == 0.0
        assert any(n.startswith("INFO:") and "Linter" in n for n in report["insufficient_evidence_notes"])


class TestSandboxIsolation:
    def test_sandbox_temp_dir_is_outside_workspace(self, tmp_path):
        workspace = str(tmp_path)
        # P2-8: the subprocess cwd is the workspace (neutral, like a normal pytest
        # run); what must be outside the workspace is where tests are collected.
        test_code = (
            "import os\ndef test_temp_dir():\n"
            f"    assert not os.path.abspath(__file__).startswith({repr(workspace)})\n"
        )
        res = SandboxRunner.execute_in_anonymous_sandbox(workspace, [("test_dir.py", test_code)])
        assert "test_temp_dir" in res["passed"]

    def test_generated_conftest_no_inspect_spoofing(self, tmp_path):
        workspace = str(tmp_path)
        test_code = (
            "import os\n"
            "def test_inspect_stack():\n"
            "    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conftest.py')\n"
            "    with open(path) as f:\n"
            "        content = f.read()\n"
            "    assert 'inspect.stack' not in content\n"
        )
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
        from unittest.mock import MagicMock, patch

        from the_judge.core.evidence import capture_evidence

        with patch("the_judge.core.evidence.generate_property_tests") as mock_gen_props, \
\
             patch("the_judge.core.evidence.SandboxRunner.execute_in_anonymous_sandbox") as mock_sandbox, \
             patch("the_judge.core.evidence.run_command") as mock_run_cmd, \
             patch("os.listdir") as mock_listdir, \
             patch("builtins.open") as mock_open:

            # Setup mock for property tests
            mock_cand = MagicMock()
            mock_cand.challenge_code = "def test_prop_judge_1():\n    pass\n"
            mock_cand.confidence = "HIGH"
            mock_gen_props.return_value = [mock_cand]

            # Mock workspace dir visible tests
            mock_listdir.return_value = ["test_workspace.py"]
            mock_open.return_value.__enter__.return_value.read.return_value = "def test_behavior_sneaky():\n    pass\n"

            # Setup mock for sandbox
            mock_sandbox.return_value = {
                "passed": ["test_prop_judge_1", "test_behavior_sneaky"],
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

            # test_prop_judge_1 was synthesized by the judge
            assert provenance["test_prop_judge_1"]["source"] == "judge_challenge_test"

            # test_behavior_sneaky should NOT be judge_challenge_test, despite "behavior_" in its name
            assert provenance["test_behavior_sneaky"]["source"] == "public_visible_test"
