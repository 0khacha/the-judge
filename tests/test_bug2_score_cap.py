"""Regression tests for Bug 2: score doesn't match README.

README shows FAIL → Score: 0.0/100.0. Actual FAIL gives 76.5.
A FAIL verdict must have score capped at ≤ 40.
An ABSTAIN verdict must have score capped at ≤ 65.
"""

from the_judge.core.score_engine import evaluate


class TestBug2ScoreCap:
    """Scores must be capped based on the verdict decision."""

    def test_fail_score_capped_at_40(self):
        """FAIL verdict must have score ≤ 40 regardless of weighted formula."""
        findings = {"requirements": [], "security_notes": [], "edge_cases": []}
        evidence = {
            "test_suite": {
                "exit_code": 1,
                "total_tests": 10,
                "passed_tests": [f"test_{i}" for i in range(9)],
                "failed_tests": ["test_critical"],
            },
            "test_provenance": {},
        }
        result = evaluate(findings, evidence)
        assert result["verdict"] == "FAIL"
        assert result["numeric_score"] <= 40.0, (
            f"FAIL verdict should have score ≤ 40, got {result['numeric_score']}"
        )

    def test_abstain_score_capped_at_65(self):
        """ABSTAIN verdict must have score ≤ 65."""
        findings = {"requirements": [], "security_notes": [], "edge_cases": []}
        evidence = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 0,
                "passed_tests": [],
                "failed_tests": [],
            },
            "test_provenance": {},
        }
        result = evaluate(findings, evidence)
        assert result["verdict"] == "ABSTAIN"
        assert result["numeric_score"] <= 65.0, (
            f"ABSTAIN verdict should have score ≤ 65, got {result['numeric_score']}"
        )

    def test_pass_score_not_capped(self):
        """PASS verdict should allow full score."""
        findings = {"requirements": [], "security_notes": [], "edge_cases": []}
        evidence = {
            "test_suite": {
                "exit_code": 0,
                "total_tests": 3,
                "passed_tests": ["test_a", "test_b", "test_challenge_prop_boundary_fn"],
                "failed_tests": [],
            },
            "test_provenance": {
                "test_a": {
                    "source": "public_visible_test",
                    "independence_level": "externally_verified",
                    "property_family": "public_workspace_tests",
                },
                "test_b": {
                    "source": "public_visible_test",
                    "independence_level": "externally_verified",
                    "property_family": "public_workspace_tests",
                },
                "test_challenge_prop_boundary_fn": {
                    "source": "judge_challenge_test",
                    "independence_level": "externally_verified",
                    "property_family": "prop_boundary",
                },
            },
        }
        result = evaluate(findings, evidence)
        assert result["verdict"] == "PASS"
        assert result["numeric_score"] > 65.0, (
            f"PASS verdict should have unrestricted score, got {result['numeric_score']}"
        )
