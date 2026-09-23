"""
Tests for the CritiqueEngine, AuditTrail, and adversarial improvement philosophy.

Covers all tests specified in the design document:
  - CritiqueEngine (evidence classification, contradictions, assumptions)
  - Stop Logic (high score does NOT stop with critical blockers)
  - Evidence (agent claims are not treated as evidence)
  - AuditTrail (round history, resolution tracking)
  - Visual evidence (screenshots only for visual projects)
  - Regression (improvement cannot hide previous failures)
"""

import json
import os
import tempfile
import textwrap
from typing import Any
from unittest.mock import MagicMock

import pytest

from the_judge.core.critique_engine import (
    CritiqueEngine,
    CritiqueFinding,
    EvidenceLevel,
    EvidenceSufficiency,
    FindingResolution,
    FindingSeverity,
    ProjectDomain,
)
from the_judge.integrations.audit_trail import AuditTrail, RoundRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ground_truth(
    passed: list[str] = None,
    failed: list[str] = None,
    errors: dict[str, str] = None,
    evidence_level: int = 0,
    challenge_tampered: bool = False,
    missing_challenges: list[str] = None,
) -> dict[str, Any]:
    passed = passed or []
    failed = failed or []
    return {
        "test_suite": {
            "total_tests": len(passed) + len(failed),
            "passed_tests": passed,
            "failed_tests": failed,
            "errors": errors or {},
        },
        "test_provenance": {t: {"independence_level": "agent_controlled"} for t in passed},
        "challenge_manifest": {
            "file_tampered": challenge_tampered,
            "missing_challenges": missing_challenges or [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
    }


def _make_verification_result(
    decision: str = "FAIL",
    score: float = 50.0,
    evidence_level: int = 1,
    findings: list = None,
    blocking_issues: list = None,
) -> MagicMock:
    vr = MagicMock()
    vr.decision = decision
    vr.numeric_score = score
    vr.findings = findings or []
    vr.blocking_issues = blocking_issues or []
    vr.insufficient_notes = []
    vr.trust_profile = {"evidence_level": evidence_level}
    vr.provenance = {}
    return vr


def _make_workspace_with_py(content: str, test_content: str = "") -> str:
    """Create a temp workspace with a Python module and optional test file."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "module.py"), "w") as f:
        f.write(content)
    if test_content:
        with open(os.path.join(d, "test_module.py"), "w") as f:
            f.write(test_content)
    return d


def _make_workspace_with_html(content: str) -> str:
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "index.html"), "w") as f:
        f.write(content)
    return d


# ====================================
# CritiqueEngine Tests
# ====================================


class TestEvidenceLevelClassification:
    def test_evidence_backed_finding_from_test_failure(self):
        """A failed test produces an EVIDENCE_BACKED finding."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(failed=["test_cache_expiration"])
        vr = _make_verification_result()
        workspace = _make_workspace_with_py("def cache(): pass")

        result = engine.critique(workspace, vr, gt)

        ev_backed = [
            f for f in result.findings if f.evidence_level == EvidenceLevel.EVIDENCE_BACKED
        ]
        assert len(ev_backed) >= 1, (
            "Expected at least one EVIDENCE_BACKED finding from test failure"
        )
        assert any("test_cache_expiration" in f.description for f in ev_backed)

    def test_observed_finding_from_code_scan(self):
        """A silent except block in code produces an OBSERVED finding (no test needed)."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(passed=["test_something"])
        vr = _make_verification_result(decision="PASS", score=80.0)
        workspace = _make_workspace_with_py(
            textwrap.dedent("""\
            def process(x):
                try:
                    return x / 0
                except Exception:
                    pass
        """)
        )

        result = engine.critique(workspace, vr, gt)

        observed = [f for f in result.findings if f.evidence_level == EvidenceLevel.OBSERVED]
        # Should detect the silent broad exception
        assert any(
            "ilent" in f.description or "exception" in f.description.lower() for f in observed
        ), f"Expected OBSERVED finding for silent except, got: {[f.description for f in observed]}"

    def test_unverified_assumption_no_none_tests(self):
        """When no None/empty tests exist, assumption is reported."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(passed=["test_basic_case", "test_another_case"])
        vr = _make_verification_result(decision="PASS", score=75.0)
        workspace = _make_workspace_with_py("def process(x):\n    return x * 2\n")

        result = engine.critique(workspace, vr, gt)

        assert any(
            "None" in a or "null" in a or "empty" in a for a in result.unverified_assumptions
        ), f"Expected None-input assumption, got: {result.unverified_assumptions}"

    def test_agent_claim_from_assertive_docstring(self):
        """Assertive language in docstrings is classified as AGENT_CLAIM."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(passed=["test_one"])
        vr = _make_verification_result(decision="PASS", score=80.0)
        workspace = _make_workspace_with_py(
            textwrap.dedent('''\
            def authenticate(token):
                """Always returns True for valid tokens. Handles all cases."""
                return True
        ''')
        )

        result = engine.critique(workspace, vr, gt)

        agent_claims = [f for f in result.findings if f.evidence_level == EvidenceLevel.AGENT_CLAIM]
        assert len(agent_claims) >= 1, (
            f"Expected AGENT_CLAIM finding for assertive docstring, got: {[f.description for f in result.findings]}"
        )

    def test_contradicted_claim_from_tampered_test(self):
        """Tampered challenge file produces a CONTRADICTED finding."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(challenge_tampered=True)
        vr = _make_verification_result()
        workspace = _make_workspace_with_py("def f(): pass")

        result = engine.critique(workspace, vr, gt)

        contradicted = [
            f for f in result.findings if f.evidence_level == EvidenceLevel.CONTRADICTED
        ]
        assert len(contradicted) >= 1, "Expected CONTRADICTED finding from tampered test file"

    def test_contradicted_missing_challenges(self):
        """Missing expected challenge tests → CONTRADICTED."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(missing_challenges=["test_edge_case_1", "test_security_check"])
        vr = _make_verification_result()
        workspace = _make_workspace_with_py("def f(): pass")

        result = engine.critique(workspace, vr, gt)

        contradicted = [
            f for f in result.findings if f.evidence_level == EvidenceLevel.CONTRADICTED
        ]
        assert any(
            "missing" in f.description.lower() or "challenge" in f.description.lower()
            for f in contradicted
        ), "Expected CONTRADICTED finding for missing challenges"


class TestEvidenceVsSeverityAreIndependent:
    def test_evidence_backed_low_is_not_a_blocker(self):
        """EVIDENCE_BACKED + LOW severity must NOT be a blocker."""
        finding = CritiqueFinding(
            id="TEST-001",
            question="What is wrong?",
            description="Minor style issue",
            evidence_level=EvidenceLevel.EVIDENCE_BACKED,
            severity=FindingSeverity.LOW,
        )
        assert not finding.is_blocker(), "EVIDENCE_BACKED + LOW should NOT be a blocker"

    def test_contradicted_critical_is_always_blocker(self):
        """CONTRADICTED + CRITICAL must always be a blocker."""
        finding = CritiqueFinding(
            id="TEST-002",
            question="What contradicts?",
            description="Agent claims all tests pass but test_auth failed",
            evidence_level=EvidenceLevel.CONTRADICTED,
            severity=FindingSeverity.CRITICAL,
        )
        assert finding.is_blocker(), "CONTRADICTED + CRITICAL must be a blocker"

    def test_contradicted_high_is_blocker(self):
        """CONTRADICTED + HIGH must be a blocker."""
        finding = CritiqueFinding(
            id="TEST-003",
            question="What contradicts?",
            description="Contradiction on high-impact claim",
            evidence_level=EvidenceLevel.CONTRADICTED,
            severity=FindingSeverity.HIGH,
        )
        assert finding.is_blocker()

    def test_observed_medium_is_not_blocker(self):
        """OBSERVED + MEDIUM should not block the loop."""
        finding = CritiqueFinding(
            id="TEST-004",
            question="What is observed?",
            description="Missing type annotation on 3 functions",
            evidence_level=EvidenceLevel.OBSERVED,
            severity=FindingSeverity.MEDIUM,
        )
        assert not finding.is_blocker(), "OBSERVED + MEDIUM should not be a blocker"

    def test_agent_claim_any_severity_is_not_blocker(self):
        """AGENT_CLAIM should never be a blocker regardless of severity."""
        for sev in FindingSeverity:
            finding = CritiqueFinding(
                id=f"TEST-CLM-{sev}",
                question="What is unsupported?",
                description="Agent claim with no backing",
                evidence_level=EvidenceLevel.AGENT_CLAIM,
                severity=sev,
            )
            assert not finding.is_blocker(), f"AGENT_CLAIM + {sev} should not be a blocker"

    def test_evidence_backed_critical_is_blocker(self):
        """EVIDENCE_BACKED + CRITICAL must be a blocker."""
        finding = CritiqueFinding(
            id="TEST-005",
            question="What is wrong?",
            description="Critical test failure with concrete evidence",
            evidence_level=EvidenceLevel.EVIDENCE_BACKED,
            severity=FindingSeverity.CRITICAL,
        )
        assert finding.is_blocker()


# ====================================
# Stop Logic Tests
# ====================================


class TestStopLogic:
    """Tests that the loop does NOT stop on score alone."""

    def _make_loop(self, **kwargs):
        from the_judge.integrations.repair_loop import AgentRepairLoop

        return AgentRepairLoop(max_rounds=3, quality_threshold=90.0, **kwargs)

    def test_high_score_does_not_stop_with_critical_contradiction(self):
        """Loop must continue if a CONTRADICTED + CRITICAL finding exists, even at score 94."""
        from the_judge.integrations.repair_loop import AgentRepairLoop

        loop = AgentRepairLoop(max_rounds=3, quality_threshold=90.0)

        vr = _make_verification_result(decision="PASS", score=94.0, evidence_level=3)
        quality = {"score": 94.0, "threshold": 90.0, "weaknesses": [], "passed": True}

        critique_result = MagicMock()
        contradiction = CritiqueFinding(
            id="CRIT-CONTRA-001",
            question="What contradicts?",
            description="Agent claimed all tests pass but test_auth.py::test_expired_token FAILED",
            evidence_level=EvidenceLevel.CONTRADICTED,
            severity=FindingSeverity.CRITICAL,
        )
        critique_result.findings = [contradiction]
        critique_result.has_blockers.return_value = True
        critique_result.evidence_sufficiency = EvidenceSufficiency(
            level="sufficient",
            independent_tests=2,
            agent_controlled_tests=5,
            has_contradictions=True,
            reasons=[],
            summary="",
        )

        should_stop, reason = loop._should_stop(vr, quality, critique_result)
        assert not should_stop, (
            f"Loop must NOT stop with CONTRADICTED + CRITICAL finding. Got: {reason}"
        )
        assert "blocker" in reason.lower()

    def test_high_score_does_not_stop_with_critical_evidence_backed_finding(self):
        """Loop must continue if EVIDENCE_BACKED + CRITICAL finding exists."""
        from the_judge.integrations.repair_loop import AgentRepairLoop

        loop = AgentRepairLoop(max_rounds=3, quality_threshold=90.0)

        vr = _make_verification_result(decision="PASS", score=92.0, evidence_level=3)
        quality = {"score": 92.0, "threshold": 90.0, "weaknesses": [], "passed": True}

        critique_result = MagicMock()
        critical_finding = CritiqueFinding(
            id="CRIT-FAIL-001",
            question="What is wrong?",
            description="Critical behavioral test failure",
            evidence_level=EvidenceLevel.EVIDENCE_BACKED,
            severity=FindingSeverity.CRITICAL,
        )
        critique_result.findings = [critical_finding]
        critique_result.has_blockers.return_value = True
        critique_result.evidence_sufficiency = EvidenceSufficiency(
            level="sufficient",
            independent_tests=2,
            agent_controlled_tests=3,
            has_contradictions=False,
            reasons=[],
            summary="",
        )

        should_stop, reason = loop._should_stop(vr, quality, critique_result)
        assert not should_stop
        assert "blocker" in reason.lower()

    def test_low_severity_evidence_does_not_automatically_block(self):
        """EVIDENCE_BACKED + LOW should not block the loop."""
        from the_judge.integrations.repair_loop import AgentRepairLoop

        loop = AgentRepairLoop(max_rounds=3, quality_threshold=90.0)

        vr = _make_verification_result(decision="PASS", score=91.0, evidence_level=3)
        quality = {"score": 91.0, "threshold": 90.0, "weaknesses": [], "passed": True}

        critique_result = MagicMock()
        low_finding = CritiqueFinding(
            id="CRIT-OBS-001",
            question="What is low priority?",
            description="Minor code style issue",
            evidence_level=EvidenceLevel.EVIDENCE_BACKED,
            severity=FindingSeverity.LOW,
        )
        critique_result.findings = [low_finding]
        critique_result.has_blockers.return_value = False
        critique_result.evidence_sufficiency = EvidenceSufficiency(
            level="sufficient",
            independent_tests=2,
            agent_controlled_tests=2,
            has_contradictions=False,
            reasons=[],
            summary="",
        )

        should_stop, reason = loop._should_stop(vr, quality, critique_result)
        assert should_stop, (
            f"Loop SHOULD stop when only low-severity non-blocker findings remain. Got: {reason}"
        )

    def test_stop_when_threshold_reached_and_no_blockers(self):
        """Loop should stop when all conditions are met."""
        from the_judge.integrations.repair_loop import AgentRepairLoop

        loop = AgentRepairLoop(max_rounds=3, quality_threshold=90.0)

        vr = _make_verification_result(decision="PASS", score=91.0, evidence_level=3)
        quality = {"score": 91.0, "threshold": 90.0, "weaknesses": [], "passed": True}

        critique_result = MagicMock()
        critique_result.findings = []
        critique_result.has_blockers.return_value = False
        critique_result.evidence_sufficiency = EvidenceSufficiency(
            level="sufficient",
            independent_tests=3,
            agent_controlled_tests=1,
            has_contradictions=False,
            reasons=[],
            summary="",
        )

        should_stop, reason = loop._should_stop(vr, quality, critique_result)
        assert should_stop, f"Loop SHOULD stop when all conditions met. Got: {reason}"
        assert reason == "all_conditions_met"


# ====================================
# Evidence Tests
# ====================================


class TestEvidenceClassification:
    def test_agent_claim_is_not_treated_as_evidence(self):
        """Agent-controlled tests should be classified as agent_controlled, not independent."""
        engine = CritiqueEngine()
        gt = {
            "test_suite": {
                "total_tests": 3,
                "passed_tests": ["test_a", "test_b", "test_c"],
                "failed_tests": [],
                "errors": {},
            },
            "test_provenance": {
                "test_a": {"independence_level": "agent_controlled"},
                "test_b": {"independence_level": "agent_controlled"},
                "test_c": {"independence_level": "agent_controlled"},
            },
            "challenge_manifest": {"file_tampered": False, "missing_challenges": []},
            "type_checker": {"exit_code": 0, "error_count": 0},
        }
        _make_verification_result(decision="PASS", score=80.0, evidence_level=0)

        result = engine._assess_evidence_sufficiency(gt, [])
        assert result.level == "insufficient", (
            f"All agent-controlled tests → evidence should be insufficient, got: {result.level}"
        )
        assert result.independent_tests == 0

    def test_contradiction_detected_when_score_high_but_evidence_low(self):
        """High score + low evidence level → CONTRADICTED finding."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(passed=["test_basic"])
        vr = _make_verification_result(decision="FAIL", score=85.0, evidence_level=1)

        contradictions = engine._detect_contradictions(gt, vr)
        # score > 80 but evidence_level < 2 and decision != PASS
        contra_descs = [c.get("description", "") for c in contradictions]
        assert any("score" in d.lower() or "evidence" in d.lower() for d in contra_descs), (
            f"Expected contradiction for score/evidence mismatch, got: {contra_descs}"
        )

    def test_evidence_is_attached_to_finding(self):
        """Every EVIDENCE_BACKED finding must have at least one evidence_ref."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(failed=["test_boundary_check", "test_auth_expired"])
        vr = _make_verification_result()
        workspace = _make_workspace_with_py("def boundary(): pass")

        result = engine.critique(workspace, vr, gt)

        ev_backed = [
            f for f in result.findings if f.evidence_level == EvidenceLevel.EVIDENCE_BACKED
        ]
        for f in ev_backed:
            assert f.evidence_refs, (
                f"EVIDENCE_BACKED finding '{f.id}' has no evidence_refs: {f.description}"
            )


# ====================================
# AuditTrail Tests
# ====================================


class TestAuditTrail:
    def _make_record(
        self,
        round_number: int,
        previous_score: float,
        new_score: float,
        decision: str = "FAIL",
        resolved_ids: list[str] = None,
        remaining_findings: list[dict] = None,
    ) -> RoundRecord:
        return RoundRecord(
            round_number=round_number,
            timestamp="2026-01-01T00:00:00Z",
            workspace_hash="abc123",
            domain="software_library",
            previous_score=previous_score,
            new_score=new_score,
            decision=decision,
            resolved_finding_ids=resolved_ids or [],
            remaining_findings=remaining_findings or [],
            loop_decision="continue",
        )

    def test_round_history_preserved(self):
        """AuditTrail stores all rounds in order."""
        trail = AuditTrail()
        trail.record_round(self._make_record(1, 0.0, 60.0))
        trail.record_round(self._make_record(2, 60.0, 75.0))
        trail.record_round(self._make_record(3, 75.0, 91.0, decision="PASS"))

        history = trail.get_history()
        assert len(history) == 3
        assert history[0].round_number == 1
        assert history[2].decision == "PASS"

    def test_score_progression(self):
        """Score progression tracks new_score per round."""
        trail = AuditTrail()
        trail.record_round(self._make_record(1, 0.0, 55.0))
        trail.record_round(self._make_record(2, 55.0, 78.0))

        progression = trail.get_score_progression()
        assert progression == [55.0, 78.0]

    def test_changes_are_recorded(self):
        """Improvement actions are stored per round."""
        trail = AuditTrail()
        r = self._make_record(1, 0.0, 60.0)
        r.improvement_actions = [
            "Fixed failing test_cache_expiration",
            "Added None-guard to process()",
        ]
        trail.record_round(r)

        assert trail.get_history()[0].improvement_actions == [
            "Fixed failing test_cache_expiration",
            "Added None-guard to process()",
        ]

    def test_resolved_findings_are_recorded(self):
        """Resolved finding IDs are recorded and accessible."""
        trail = AuditTrail()
        r1 = self._make_record(1, 0.0, 60.0)
        r1.resolved_finding_ids = ["CRIT-FAIL-001"]
        trail.record_round(r1)

        r2 = self._make_record(2, 60.0, 80.0)
        r2.resolved_finding_ids = ["CRIT-CONTRA-001", "CRIT-MISS-002"]
        trail.record_round(r2)

        all_resolved = trail.get_all_resolved_ids()
        assert "CRIT-FAIL-001" in all_resolved
        assert "CRIT-CONTRA-001" in all_resolved

    def test_remaining_findings_are_recorded(self):
        """Remaining open findings from the last round are accessible."""
        trail = AuditTrail()
        r = self._make_record(
            1,
            0.0,
            60.0,
            remaining_findings=[
                {"id": "CRIT-OBS-001", "description": "Missing boundary tests"},
                {"id": "CRIT-MISS-002", "description": "No error path tests"},
            ],
        )
        trail.record_round(r)

        remaining = trail.get_unresolved_findings()
        assert len(remaining) == 2
        assert any(f["id"] == "CRIT-OBS-001" for f in remaining)

    def test_score_delta_computed_correctly(self):
        """Score delta is correct per round."""
        r = RoundRecord(
            round_number=1,
            timestamp="2026-01-01T00:00:00Z",
            workspace_hash="x",
            domain="software_library",
            previous_score=45.0,
            new_score=78.0,
            decision="FAIL",
        )
        assert r.score_delta == pytest.approx(33.0, abs=0.01)

    def test_total_score_delta_computed_correctly(self):
        """Total score delta across all rounds is correct."""
        trail = AuditTrail()
        trail.record_round(self._make_record(1, 0.0, 45.0))
        trail.record_round(self._make_record(2, 45.0, 72.0))
        trail.record_round(self._make_record(3, 72.0, 91.0, decision="PASS"))

        assert trail.total_score_delta() == pytest.approx(91.0, abs=0.01)
        assert trail.initial_score() == 0.0
        assert trail.final_score() == 91.0

    def test_audit_trail_saves_to_disk(self):
        """Audit trail can be saved and re-read as valid JSON."""
        trail = AuditTrail()
        r = self._make_record(1, 0.0, 65.0)
        r.skeptic_summary = "Test skeptic summary"
        r.contradictions = [{"claim": "test claim", "description": "test desc"}]
        trail.record_round(r)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = trail.save_to_disk(tmpdir)
            assert os.path.exists(json_path)

            with open(json_path) as f:
                data = json.load(f)

            assert data["total_rounds"] == 1
            assert data["rounds"][0]["round_number"] == 1

    def test_text_summary_contains_round_info(self):
        """Human-readable text summary includes round decisions and scores."""
        trail = AuditTrail()
        trail.record_round(self._make_record(1, 0.0, 60.0))
        trail.record_round(self._make_record(2, 60.0, 91.0, decision="PASS"))

        summary = trail.generate_text_summary()
        assert "ROUND 1" in summary
        assert "ROUND 2" in summary
        assert "PASS" in summary


# ====================================
# Visual Evidence Tests
# ====================================


class TestVisualEvidence:
    def test_visual_domain_classification_for_html(self):
        """HTML workspace is classified as web_app_or_ui."""
        engine = CritiqueEngine()
        workspace = _make_workspace_with_html("<html><body><h1>Test</h1></body></html>")
        domain = engine.classify_domain(workspace)
        assert domain == ProjectDomain.WEB_APP_OR_UI

    def test_non_visual_domain_classification_for_python_library(self):
        """Python library workspace is NOT classified as visual."""
        engine = CritiqueEngine()
        workspace = _make_workspace_with_py("def process(x):\n    return x * 2\n")
        domain = engine.classify_domain(workspace)
        assert domain in (
            ProjectDomain.SOFTWARE_LIBRARY,
            ProjectDomain.CLI_SCRIPT,
        ), f"Expected non-visual domain, got: {domain}"
        assert domain != ProjectDomain.WEB_APP_OR_UI

    def test_non_visual_project_does_not_include_html_findings(self):
        """Python-only project should not produce HTML-specific findings."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(passed=["test_basic"])
        vr = _make_verification_result(decision="PASS", score=80.0)
        workspace = _make_workspace_with_py("def compute(n):\n    return n * 2\n")

        result = engine.critique(workspace, vr, gt)

        html_findings = [
            f
            for f in result.findings
            if "alt" in f.description.lower()
            or "viewport" in f.description.lower()
            or "password" in f.description.lower()
            and "type='text'" in f.description.lower()
        ]
        assert len(html_findings) == 0, (
            f"Non-visual project should not have HTML-specific findings: {[f.description for f in html_findings]}"
        )

    def test_visual_evidence_recorded_with_screenshot_field(self):
        """RoundRecord correctly stores screenshot path for visual rounds."""
        trail = AuditTrail()
        r = RoundRecord(
            round_number=1,
            timestamp="2026-01-01T00:00:00Z",
            workspace_hash="x",
            domain="web_app_or_ui",
            previous_score=0.0,
            new_score=60.0,
            decision="FAIL",
            screenshot_path="/workspace/_judge_visual/round_1_visual.png",
        )
        trail.record_round(r)
        assert trail.screenshots() == ["/workspace/_judge_visual/round_1_visual.png"]


# ====================================
# Regression Tests
# ====================================


class TestRegression:
    def test_improvement_cannot_hide_regression(self):
        """A test that passed in round N but fails in round N+1 → CONTRADICTED finding."""
        engine = CritiqueEngine()

        # Round 1 ground truth: test_auth passed
        _make_ground_truth(passed=["test_auth", "test_login"])

        # Round 2 ground truth: test_auth now fails (regression)
        gt_round2 = _make_ground_truth(passed=["test_login"], failed=["test_auth"])

        vr = _make_verification_result(
            decision="FAIL",
            score=75.0,
            blocking_issues=["REGRESSION DETECTED: test_auth was passing, now failing."],
        )

        workspace = _make_workspace_with_py("def auth(): pass")
        result = engine.critique(workspace, vr, gt_round2)

        # The REGRESSION blocking_issue should produce a CONTRADICTED finding
        contradicted = [
            f for f in result.findings if f.evidence_level == EvidenceLevel.CONTRADICTED
        ]
        assert (
            any(
                "regression" in f.description.lower() or "regression" in f.suggested_action.lower()
                for f in contradicted
            )
            or len(contradicted) >= 1
        ), "Regression from score_engine blocking_issues should produce CONTRADICTED findings"

    def test_previous_failure_remains_tracked_until_resolved(self):
        """Findings from previous round that still fail remain in still_open."""
        engine = CritiqueEngine()

        previous_findings = [
            {
                "id": "CRIT-FAIL-001",
                "evidence_level": "evidence_backed",
                "severity": "high",
                "resolution": "open",
                "evidence_refs": ["test_cache_expiration"],
                "description": "Test 'test_cache_expiration' failed",
                "is_blocker": True,
            }
        ]

        # Current ground truth: test still fails
        current_gt = _make_ground_truth(failed=["test_cache_expiration"])

        resolved_ids, still_open = engine.resolve_findings_from_previous_round(
            previous_findings, current_gt
        )

        assert "CRIT-FAIL-001" not in resolved_ids, (
            "Still-failing test should not be marked resolved"
        )
        assert any(f.get("id") == "CRIT-FAIL-001" for f in still_open), (
            "Still-failing test finding should remain in still_open"
        )

    def test_finding_resolved_when_test_now_passes(self):
        """A finding for a test failure is resolved when that test now passes."""
        engine = CritiqueEngine()

        previous_findings = [
            {
                "id": "CRIT-FAIL-001",
                "evidence_level": "evidence_backed",
                "severity": "high",
                "resolution": "open",
                "evidence_refs": ["test_cache_expiration"],
                "description": "Test 'test_cache_expiration' failed",
                "is_blocker": True,
            }
        ]

        # Current ground truth: test now passes
        current_gt = _make_ground_truth(passed=["test_cache_expiration", "test_login"])

        resolved_ids, still_open = engine.resolve_findings_from_previous_round(
            previous_findings, current_gt
        )

        assert "CRIT-FAIL-001" in resolved_ids, (
            "Passing test should cause the corresponding finding to be marked resolved"
        )
        assert not any(f.get("id") == "CRIT-FAIL-001" for f in still_open)


# ====================================
# Domain Classification Tests
# ====================================


class TestDomainClassification:
    def test_classifies_python_library(self):
        engine = CritiqueEngine()
        workspace = _make_workspace_with_py(
            "def process(data):\n    return sorted(data)\n\nclass Processor:\n    pass\n"
        )
        assert engine.classify_domain(workspace) == ProjectDomain.SOFTWARE_LIBRARY

    def test_classifies_html_as_web_app(self):
        engine = CritiqueEngine()
        workspace = _make_workspace_with_html(
            "<!DOCTYPE html><html><head></head><body><h1>Dashboard</h1></body></html>"
        )
        assert engine.classify_domain(workspace) == ProjectDomain.WEB_APP_OR_UI

    def test_classifies_data_science_with_pandas_import(self):
        engine = CritiqueEngine()
        workspace = _make_workspace_with_py(
            "import pandas as pd\nimport sklearn\ndef train(): pass\n"
        )
        assert engine.classify_domain(workspace) == ProjectDomain.DATA_SCIENCE

    def test_classifies_cli_with_argparse(self):
        engine = CritiqueEngine()
        workspace = _make_workspace_with_py(
            "import argparse\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.parse_args()\n\nif __name__ == '__main__':\n    main()\n"
        )
        assert engine.classify_domain(workspace) == ProjectDomain.CLI_SCRIPT


# ====================================
# Improvement Priority Tests
# ====================================


class TestImprovementPriority:
    def test_critical_findings_ranked_first(self):
        """CRITICAL findings must appear before MEDIUM and LOW in priority list."""
        findings = [
            CritiqueFinding(
                id="F1",
                question="Q",
                description="Low priority",
                evidence_level=EvidenceLevel.OBSERVED,
                severity=FindingSeverity.LOW,
            ),
            CritiqueFinding(
                id="F2",
                question="Q",
                description="Critical failure",
                evidence_level=EvidenceLevel.EVIDENCE_BACKED,
                severity=FindingSeverity.CRITICAL,
            ),
            CritiqueFinding(
                id="F3",
                question="Q",
                description="Medium issue",
                evidence_level=EvidenceLevel.OBSERVED,
                severity=FindingSeverity.MEDIUM,
            ),
        ]
        engine = CritiqueEngine()
        ordered = engine._prioritize_findings(findings)
        assert ordered[0].id == "F2", f"CRITICAL should be first, got: {ordered[0].id}"
        assert ordered[-1].id == "F1", f"LOW should be last, got: {ordered[-1].id}"

    def test_contradicted_ranked_before_observed_same_severity(self):
        """CONTRADICTED findings ranked before OBSERVED at same severity level."""
        findings = [
            CritiqueFinding(
                id="OBS",
                question="Q",
                description="Observed issue",
                evidence_level=EvidenceLevel.OBSERVED,
                severity=FindingSeverity.HIGH,
            ),
            CritiqueFinding(
                id="CONTRA",
                question="Q",
                description="Contradicted claim",
                evidence_level=EvidenceLevel.CONTRADICTED,
                severity=FindingSeverity.HIGH,
            ),
        ]
        engine = CritiqueEngine()
        ordered = engine._prioritize_findings(findings)
        assert ordered[0].id == "CONTRA", (
            "CONTRADICTED should rank before OBSERVED at same severity"
        )

    def test_resolved_findings_excluded_from_priority(self):
        """RESOLVED findings should not appear in the improvement priority list."""
        findings = [
            CritiqueFinding(
                id="F1",
                question="Q",
                description="Already fixed",
                evidence_level=EvidenceLevel.EVIDENCE_BACKED,
                severity=FindingSeverity.HIGH,
                resolution=FindingResolution.RESOLVED,
            ),
            CritiqueFinding(
                id="F2",
                question="Q",
                description="Still open",
                evidence_level=EvidenceLevel.OBSERVED,
                severity=FindingSeverity.MEDIUM,
            ),
        ]
        engine = CritiqueEngine()
        ordered = engine._prioritize_findings(findings)
        ids = [f.id for f in ordered]
        assert "F1" not in ids, "RESOLVED finding must not appear in priority list"
        assert "F2" in ids


# ====================================
# CritiqueResult Structure Tests
# ====================================


class TestCritiqueResultStructure:
    def test_critique_result_to_dict_has_required_fields(self):
        """CritiqueResult.to_dict() must contain all required fields."""
        engine = CritiqueEngine()
        gt = _make_ground_truth()
        vr = _make_verification_result()
        workspace = _make_workspace_with_py("def f(): pass")

        result = engine.critique(workspace, vr, gt)
        d = result.to_dict()

        required = [
            "domain",
            "findings",
            "unverified_assumptions",
            "contradictions",
            "missing_evidence",
            "agent_claims_unchecked",
            "evidence_sufficiency",
            "skeptic_summary",
            "improvement_priority",
            "has_blockers",
            "open_findings_count",
            "blocker_count",
        ]
        for key in required:
            assert key in d, f"Missing required field in CritiqueResult.to_dict(): '{key}'"

    def test_skeptic_summary_not_empty(self):
        """Skeptic summary should always be produced."""
        engine = CritiqueEngine()
        gt = _make_ground_truth(failed=["test_boundary"])
        vr = _make_verification_result()
        workspace = _make_workspace_with_py("def f(): pass")

        result = engine.critique(workspace, vr, gt)
        assert result.skeptic_summary, "Skeptic summary should never be empty"
        assert len(result.skeptic_summary) > 20

    def test_finding_to_dict_has_is_blocker_field(self):
        """CritiqueFinding.to_dict() must include 'is_blocker'."""
        f = CritiqueFinding(
            id="X",
            question="Q",
            description="Test",
            evidence_level=EvidenceLevel.EVIDENCE_BACKED,
            severity=FindingSeverity.HIGH,
        )
        d = f.to_dict()
        assert "is_blocker" in d
        assert d["is_blocker"] is True  # EVIDENCE_BACKED + HIGH → blocker
