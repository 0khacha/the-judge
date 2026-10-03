"""Regression tests for Bug 1: false PASS verdicts.

These tests verify that the Judge does not return PASS for workspaces with:
  1a) No user tests (only auto-generated probes that bail on TypeError)
  1b) Vacuous tests (assert True, no assertions, no target module reference)
  1c) Hardcoded return values detectable by multi-input probes
"""

import os
import textwrap

import pytest

from the_judge.api import verify
from the_judge.core.score_engine import evaluate


class TestBug1FalsePass:
    """verify() must not return PASS for insufficient evidence."""

    # --- 1a: No workspace tests, only probes ---

    def test_1a_only_judge_probes_not_pass(self):
        """Only judge-synthesized probes passed (no user tests). Must not PASS.

        Root cause: probes that bail on TypeError via 'return' are counted as
        passed tests, granting both 'independent evidence' and 'challenge evidence'.
        """
        evidence = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 1,
                "passed_tests": ["test_behavior_idempotency_m_add"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_behavior_idempotency_m_add": {
                    "source": "judge_challenge_test",
                    "independence_level": "externally_verified",
                    "property_family": "prop_idempotency",
                }
            },
        }
        result = verify(".", _ground_truth=evidence)
        assert result.decision != "PASS", (
            f"Got {result.decision} with score {result.numeric_score}. "
            "Judge probes alone (no workspace tests) must not yield PASS."
        )

    def test_1a_score_engine_probes_only_not_pass(self):
        """Score engine level: only judge probes, no workspace tests."""
        findings = {"requirements": [], "security_notes": [], "edge_cases": []}
        evidence = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 1,
                "passed_tests": ["test_behavior_idempotency_m_add"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_behavior_idempotency_m_add": {
                    "source": "judge_challenge_test",
                    "independence_level": "externally_verified",
                    "property_family": "prop_idempotency",
                }
            },
        }
        result = evaluate(findings, evidence)
        assert result["verdict"] != "PASS", (
            f"Score engine returned {result['verdict']}. "
            "Only judge probes without workspace tests must not yield PASS."
        )

    # --- 1b: Vacuous test ---

    def test_1b_vacuous_test_filtered(self):
        """Vacuous test (assert True) plus bailed probe must not PASS.

        The vacuous_tests field tells the score engine to exclude test_x
        from evidence counts.
        """
        evidence = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 2,
                "passed_tests": ["test_x", "test_behavior_idempotency_m_add"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_x": {
                    "source": "public_visible_test",
                    "independence_level": "externally_verified",
                    "property_family": "public_workspace_tests",
                },
                "test_behavior_idempotency_m_add": {
                    "source": "judge_challenge_test",
                    "independence_level": "externally_verified",
                    "property_family": "prop_idempotency",
                },
            },
            "vacuous_tests": ["test_x"],
        }
        result = verify(".", _ground_truth=evidence)
        assert result.decision != "PASS", (
            f"Got {result.decision}. Vacuous tests must not count as evidence."
        )

    # --- 1c: Hardcoded return ---

    def test_1c_no_challenge_evidence_not_pass(self):
        """1c: workspace test passes but NO challenge probes succeeded.

        After the probe skip fix, probes that bail on TypeError are skipped
        (not in passed_tests). Without challenge evidence, synthesis evasion
        blocks PASS.
        """
        evidence = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 1,
                "passed_tests": ["test_add"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_add": {
                    "source": "public_visible_test",
                    "independence_level": "externally_verified",
                    "property_family": "public_workspace_tests",
                },
            },
        }
        result = verify(".", _ground_truth=evidence)
        assert result.decision != "PASS", (
            f"Got {result.decision} score {result.numeric_score}. "
            "Without challenge evidence, synthesis evasion must block PASS."
        )

    # --- Vacuous test detector ---

    def test_vacuous_detector_assert_true(self):
        """_detect_vacuous_tests: 'assert True' is vacuous."""
        from the_judge.core.evidence import _detect_vacuous_tests

        code = "def test_x(): assert True\n"
        result = _detect_vacuous_tests(code, {"m"})
        assert "test_x" in result

    def test_vacuous_detector_no_assertions(self):
        """_detect_vacuous_tests: test with no assertions is vacuous."""
        from the_judge.core.evidence import _detect_vacuous_tests

        code = "def test_y(): pass\n"
        result = _detect_vacuous_tests(code, {"m"})
        assert "test_y" in result

    def test_vacuous_detector_no_target_reference(self):
        """_detect_vacuous_tests: test that never references target module is vacuous."""
        from the_judge.core.evidence import _detect_vacuous_tests

        code = "def test_z(): assert 1 + 1 == 2\n"
        result = _detect_vacuous_tests(code, {"m"})
        assert "test_z" in result

    def test_vacuous_detector_real_test_not_vacuous(self):
        """_detect_vacuous_tests: test that imports and asserts on target is NOT vacuous."""
        from the_judge.core.evidence import _detect_vacuous_tests

        code = "from m import add\ndef test_add(): assert add(1, 2) == 3\n"
        result = _detect_vacuous_tests(code, {"m"})
        assert "test_add" not in result

    # --- Behavior engine probes ---

    def test_probe_skips_on_type_error(self):
        """Probes must use pytest.skip, not return, on TypeError."""
        import tempfile
        import shutil
        from the_judge.core.behavior_engine import BehaviorEngine

        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "m.py"), "w") as f:
                f.write("def add(a: int, b: int) -> int: return a + b\n")
            engine = BehaviorEngine()
            probes = engine.generate_behavioral_probes(tmp)
            assert probes, "Expected probes for m.py"
            for probe in probes:
                code = probe.executable_code
                # After the TypeError catch, the code should use pytest.skip, not bare return
                assert "pytest.skip" in code, (
                    f"Probe '{probe.property_kind}' catches TypeError but doesn't "
                    "use pytest.skip — bailed probes must not count as passed."
                )
        finally:
            shutil.rmtree(tmp)

    def test_multi_input_variance_probe_generated(self):
        """Functions with parameters must get a multi-input variance probe."""
        import tempfile
        import shutil
        from the_judge.core.behavior_engine import BehaviorEngine

        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "m.py"), "w") as f:
                f.write("def add(a: int, b: int) -> int: return a + b\n")
            engine = BehaviorEngine()
            probes = engine.generate_behavioral_probes(tmp)
            variance_probes = [p for p in probes if "multi_input" in p.property_kind]
            assert len(variance_probes) > 0, (
                "Expected a multi-input variance probe for add(a, b)"
            )
        finally:
            shutil.rmtree(tmp)

    # --- Full pipeline tests ---

    def test_1a_full_pipeline(self, tmp_path):
        """Full pipeline: workspace with only m.py, no tests → not PASS."""
        (tmp_path / "m.py").write_text("def add(a, b): return a - b\n")
        result = verify(str(tmp_path))
        assert result.decision != "PASS", (
            f"Got {result.decision} score {result.numeric_score}."
        )

    def test_1b_full_pipeline(self, tmp_path):
        """Full pipeline: m.py + vacuous test → not PASS."""
        (tmp_path / "m.py").write_text("def add(a, b): return a - b\n")
        (tmp_path / "test_m.py").write_text("def test_x(): assert True\n")
        result = verify(str(tmp_path))
        assert result.decision != "PASS", (
            f"Got {result.decision} score {result.numeric_score}."
        )

    def test_1c_full_pipeline(self, tmp_path):
        """Full pipeline: hardcoded return + single-point test → not PASS."""
        (tmp_path / "m.py").write_text("def add(a, b): return 5\n")
        (tmp_path / "test_m.py").write_text(
            "from m import add\ndef test_add(): assert add(2, 3) == 5\n"
        )
        result = verify(str(tmp_path))
        assert result.decision != "PASS", (
            f"Got {result.decision} score {result.numeric_score}."
        )

    # --- Critical coverage gate ---

    def test_critical_50pct_coverage_not_pass(self):
        """Critical coverage < 100% must not PASS (partially verified is not enough)."""
        from the_judge.core.contract_engine import ContractEngine

        spec = {
            "requirements": [
                {"id": "REQ-001", "description": "Must do X", "priority": "critical"},
                {"id": "REQ-002", "description": "Must do Y", "priority": "critical"},
            ]
        }
        engine = ContractEngine(task_spec=spec)
        ground_truth = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 1,
                "passed_tests": ["test_req_001"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_req_001": {
                    "source": "public_visible_test",
                    "independence_level": "externally_verified",
                    "property_family": "public_workspace_tests",
                }
            },
        }
        findings = {"requirements": [], "security_notes": []}
        coverage = engine.evaluate_contract_coverage(ground_truth, findings)

        # REQ-002 has no test → should be in unverified critical list
        assert "REQ-002" in coverage["summary"]["critical_unverified_ids"], (
            f"REQ-002 with no test evidence must be in critical_unverified_ids. "
            f"Got: {coverage['summary']['critical_unverified_ids']}"
        )
