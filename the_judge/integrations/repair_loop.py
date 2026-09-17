"""
Agent Improvement Loop — Critique-Driven Multi-Round Refinement.

Philosophy
----------
A high score alone is NOT sufficient to stop the loop.

Stopping requires ALL of:
  1. quality_threshold reached
  2. No unresolved CRITICAL or HIGH findings (evidence-backed or contradicted)
  3. No unresolved CONTRADICTED findings (any severity, material claims)
  4. Evidence sufficiency is not "insufficient"
  5. Further iterations are unlikely to produce meaningful improvement

The CritiqueEngine acts as an independent adversarial layer. Its findings are
classified by evidence level AND severity. These two dimensions are separate:

  EVIDENCE_BACKED + LOW   → does NOT block the loop
  CONTRADICTED + CRITICAL → ALWAYS blocks the loop

The loop passes the full critique result to the repair callback so the agent
can prioritise the most consequential, evidence-backed weaknesses first.
"""

import copy
import hashlib
import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from the_judge.api import verify
from the_judge.core.decision import VerificationResult
from the_judge.core.evidence import capture_evidence
from the_judge.integrations.agent_adapter import AgentAdapter
from the_judge.integrations.audit_trail import AuditTrail, RoundRecord


QualityEvaluator = Callable[[str, Dict[str, Any]], Dict[str, Any]]
RepairCallbackResult = Union[bool, Mapping[str, Any]]


class AgentRepairLoop:
    """Evidence-led, critique-driven multi-round improvement loop.

    Stop Conditions (ALL must hold)
    --------------------------------
    1. Quality score >= quality_threshold.
    2. No open CRITICAL or HIGH findings (evidence-backed or contradicted).
    3. No open CONTRADICTED findings on material claims.
    4. Evidence sufficiency is not "insufficient" (unless require_evidence_sufficiency=False).
    5. Repair callback did not produce a no-op.

    What gets passed to the repair callback
    ----------------------------------------
    feedback = {
        # From Judge (verification)
        "decision": "PASS" | "FAIL" | "ABSTAIN",
        "numeric_score": float,
        "findings": [...],          # Judge structured findings
        "blocking_issues": [...],
        "quality_evaluation": {...},

        # From CritiqueEngine (independent adversarial critique)
        "critique": {
            "domain": str,
            "skeptic_summary": str,
            "improvement_priority": [...],   # ordered: most critical first
            "findings": [...],               # each with evidence_level + severity
            "unverified_assumptions": [...],
            "contradictions": [...],
            "agent_claims_unchecked": [...],
            "missing_evidence": [...],
            "evidence_sufficiency": {...},
            "has_blockers": bool,
        },

        # Meta
        "round_number": int,
        "is_visual": bool,
        "visual_inspection": {...},
        "audit_trail": [...],        # round history to date
    }
    """

    _IGNORED_DIRECTORIES = frozenset({
        ".git", ".hg", ".svn", ".mypy_cache", ".pytest_cache",
        ".ruff_cache", "__pycache__", "node_modules", ".venv", "venv",
    })

    def __init__(
        self,
        adapter: Optional[AgentAdapter] = None,
        max_rounds: int = 5,
        quality_threshold: float = 90.0,
        quality_evaluator: Optional[QualityEvaluator] = None,
        require_evidence_sufficiency: bool = True,
    ):
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")
        if not 0 <= quality_threshold <= 100:
            raise ValueError("quality_threshold must be between 0 and 100")

        self.adapter = adapter or AgentAdapter()
        self.max_rounds = max_rounds
        self.quality_threshold = float(quality_threshold)
        self.quality_evaluator = quality_evaluator
        self.require_evidence_sufficiency = require_evidence_sufficiency
        self.rounds_history: List[Dict[str, Any]] = []

    def run_repair_loop(
        self,
        workspace: str,
        agent_repair_func: Callable[[str, Dict[str, Any]], RepairCallbackResult],
        task_spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the adversarial improvement loop.

        Each round:
          1. Collect ground-truth evidence (sandbox execution).
          2. Verify against Judge hard gates.
          3. Run independent CritiqueEngine — classify findings by evidence level.
          4. Evaluate quality dimensions.
          5. Determine if stopping conditions are all met.
          6. If not: build prioritised feedback, call repair callback.
          7. Verify actual workspace changes were made.
          8. Record round in AuditTrail.
        """
        from the_judge.core.visual_engine import VisualEngine
        from the_judge.core.critique_engine import CritiqueEngine

        self.rounds_history.clear()
        audit_trail = AuditTrail()
        previous_evidence: Optional[Dict[str, Any]] = None
        previous_critique_findings: List[Dict[str, Any]] = []
        previous_score: float = 0.0

        critique_engine = CritiqueEngine()
        visual_engine = VisualEngine(workspace)
        is_visual, target_visual_file = visual_engine.is_visual_workspace()

        artifacts_dir = (
            os.path.join(workspace, "_judge_visual")
            if os.path.isdir(workspace)
            else os.path.join(os.path.dirname(workspace), "_judge_visual")
        )
        previous_screenshot: Optional[str] = None

        for round_idx in range(1, self.max_rounds + 1):
            # ----------------------------------------------------------
            # 1. Capture evidence
            # ----------------------------------------------------------
            current_evidence = capture_evidence(workspace, task_spec=task_spec)
            implementation_hash = self._compute_implementation_hash(workspace)

            # ----------------------------------------------------------
            # 2. Verify (Judge hard gates + score)
            # ----------------------------------------------------------
            verification_result: VerificationResult = verify(
                workspace=workspace,
                task_spec=task_spec,
                previous_evidence=previous_evidence,
            )
            verification_feedback = self.adapter.result_to_feedback(verification_result)

            # ----------------------------------------------------------
            # 3. Independent adversarial critique
            # ----------------------------------------------------------
            critique_result = critique_engine.critique(
                workspace=workspace,
                verification_result=verification_result,
                ground_truth=current_evidence,
                previous_round=self.rounds_history[-1] if self.rounds_history else None,
            )

            # Resolve previous round's findings against current evidence
            resolved_ids: List[str] = []
            if previous_critique_findings:
                resolved_ids, _ = critique_engine.resolve_findings_from_previous_round(
                    previous_critique_findings, current_evidence
                )

            # Track new finding IDs (appeared this round)
            prev_ids = {f.get("id") for f in previous_critique_findings}
            new_ids = [f.id for f in critique_result.findings if f.id not in prev_ids]

            # ----------------------------------------------------------
            # 4. Quality evaluation
            # ----------------------------------------------------------
            quality = self._evaluate_quality(workspace, verification_result, critique_result)

            # ----------------------------------------------------------
            # 5. Visual evidence (conditional — only for visual projects)
            # ----------------------------------------------------------
            current_screenshot: Optional[str] = None
            visual_eval: Dict[str, Any] = {"is_visual": False}

            if is_visual and target_visual_file:
                current_screenshot = visual_engine.capture_screenshot(
                    target_visual_file, round_idx, artifacts_dir
                )
                visual_eval = visual_engine.evaluate_visual_aspects(
                    target_visual_file, current_screenshot, previous_screenshot
                )
                previous_screenshot = current_screenshot

                # Merge visual weaknesses into quality
                for vis_w in visual_eval.get("weaknesses", []):
                    if not any(w.get("id") == vis_w.get("id") for w in quality["weaknesses"]):
                        quality["weaknesses"].append(vis_w)
                        quality["score"] = min(quality["score"], visual_eval.get("score", quality["score"]))

            # ----------------------------------------------------------
            # 6. Check all stop conditions
            # ----------------------------------------------------------
            can_stop, stop_reason = self._should_stop(
                verification_result, quality, critique_result
            )

            # ----------------------------------------------------------
            # 7. Build round record for audit trail
            # ----------------------------------------------------------
            round_record: Dict[str, Any] = {
                "round_id": f"ROUND-{round_idx}",
                "round_number": round_idx,
                "workspace_hash": verification_result.provenance.get("workspace_hash", ""),
                "implementation_hash": implementation_hash,
                "judge_version": "v4.0",
                "is_visual": is_visual,
                "target_visual_file": target_visual_file if is_visual else None,
                "screenshot": current_screenshot,
                "visual_inspection": visual_eval,
                "decision": verification_result.decision,
                "numeric_score": verification_result.numeric_score,
                "quality": quality,
                "findings": [f.to_dict() for f in verification_result.findings],
                "blocking_issues": verification_result.blocking_issues,
                "critique": critique_result.to_dict(),
                "evidence_summary": {
                    "passed_tests": verification_result.provenance.get("passed_tests", 0),
                    "failed_tests": verification_result.provenance.get("failed_tests", 0),
                    "evidence_level": verification_result.provenance.get("evidence_level", 0),
                    "evidence_sufficiency": critique_result.evidence_sufficiency.level,
                },
                "resolved_finding_ids": resolved_ids,
                "new_finding_ids": new_ids,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self.rounds_history.append(round_record)

            # Audit trail record
            audit_record = RoundRecord(
                round_number=round_idx,
                timestamp=round_record["timestamp"],
                workspace_hash=round_record["workspace_hash"],
                domain=critique_result.domain,
                previous_score=previous_score,
                new_score=verification_result.numeric_score,
                decision=verification_result.decision,
                judge_findings=[f.to_dict() for f in verification_result.findings],
                blocking_issues=verification_result.blocking_issues,
                critique_findings=[f.to_dict() for f in critique_result.findings],
                unverified_assumptions=critique_result.unverified_assumptions,
                contradictions=critique_result.contradictions,
                agent_claims_unchecked=critique_result.agent_claims_unchecked,
                missing_evidence=critique_result.missing_evidence,
                evidence_sufficiency=critique_result.evidence_sufficiency.level,
                has_blockers=critique_result.has_blockers(),
                skeptic_summary=critique_result.skeptic_summary,
                evidence_summary=round_record["evidence_summary"],
                resolved_finding_ids=resolved_ids,
                new_finding_ids=new_ids,
                remaining_findings=[f.to_dict() for f in critique_result.get_open_findings()],
                screenshot_path=current_screenshot,
                visual_score=visual_eval.get("score") if is_visual else None,
            )

            # ----------------------------------------------------------
            # 8. Stop if all conditions met
            # ----------------------------------------------------------
            if can_stop:
                audit_record.loop_decision = "stop"
                audit_record.stop_reason = stop_reason
                audit_trail.record_round(audit_record)
                round_record["audit_record"] = audit_record.to_dict()
                return self._complete(
                    "PASS", round_idx, verification_result, quality, audit_trail
                )

            # ----------------------------------------------------------
            # 9. Not stopping: build feedback and call repair
            # ----------------------------------------------------------
            previous_evidence = copy.deepcopy(current_evidence)
            previous_critique_findings = [f.to_dict() for f in critique_result.findings]
            previous_score = verification_result.numeric_score

            if round_idx == self.max_rounds:
                audit_record.loop_decision = "stop"
                audit_record.stop_reason = "max_rounds_reached"
                audit_trail.record_round(audit_record)
                break

            feedback = self._build_improvement_feedback(
                verification_feedback,
                quality,
                critique_result,
                round_idx,
                is_visual,
                visual_eval,
                audit_trail,
            )

            repair_before_hash = self._compute_implementation_hash(workspace)
            repair_result = agent_repair_func(workspace, feedback)
            repaired, repair_summary = self._normalise_repair_result(repair_result)

            round_record["repair"] = {
                "attempted": True,
                "reported_improved": repaired,
                "summary": repair_summary,
            }
            audit_record.improvement_actions = [repair_summary] if repair_summary else []
            audit_record.changes_summary = repair_summary or ""

            if not repaired:
                audit_record.loop_decision = "abort"
                audit_record.stop_reason = "repair_callback_returned_false"
                audit_trail.record_round(audit_record)
                return self._abort(
                    "ABORTED",
                    "Agent repair callback returned False (unable to make an improvement).",
                    round_idx,
                    verification_result,
                    quality,
                    audit_trail,
                )

            repair_after_hash = self._compute_implementation_hash(workspace)
            workspace_changed = repair_before_hash != repair_after_hash
            round_record["repair"]["workspace_changed"] = workspace_changed

            if not workspace_changed:
                audit_record.loop_decision = "abort"
                audit_record.stop_reason = "no_workspace_change"
                audit_trail.record_round(audit_record)
                return self._abort(
                    "NO_MEANINGFUL_IMPROVEMENT",
                    "The repair callback reported success but did not change the workspace.",
                    round_idx,
                    verification_result,
                    quality,
                    audit_trail,
                )

            audit_record.loop_decision = "continue"
            audit_trail.record_round(audit_record)
            round_record["audit_record"] = audit_record.to_dict()

        # Max rounds exceeded
        last = self.rounds_history[-1]
        return {
            "outcome": "MAX_ROUNDS_EXCEEDED",
            "total_rounds": self.max_rounds,
            "final_decision": last["decision"],
            "quality": last["quality"],
            "history": self.rounds_history,
            "final_result": last,
            "audit_trail": audit_trail.to_dict(),
        }

    # -----------------------------------------------------------------------
    # Stop Condition Logic
    # -----------------------------------------------------------------------

    def _should_stop(
        self,
        verification_result: VerificationResult,
        quality: Dict[str, Any],
        critique_result: Any,  # CritiqueResult
    ) -> Tuple[bool, str]:
        """Determine whether all loop-stopping conditions are satisfied.

        A high score alone is NOT sufficient to stop. All conditions must hold.
        """
        from the_judge.core.critique_engine import FindingSeverity, EvidenceLevel, FindingResolution

        # Condition 1: Quality threshold
        if quality["score"] < self.quality_threshold:
            return False, f"quality_score {quality['score']:.1f} < threshold {self.quality_threshold}"

        # Condition 2: No unresolved CRITICAL or HIGH judge findings
        judge_critical_high = [
            f for f in verification_result.findings
            if f.severity in ("critical", "high", "blocking")
            and getattr(f, "resolution", "open") == "open"
        ]
        if judge_critical_high:
            return False, f"{len(judge_critical_high)} unresolved critical/high Judge finding(s)"

        # Condition 3: No evidence-backed or contradicted blocker findings from critique
        if critique_result.has_blockers():
            blockers = [f for f in critique_result.findings if f.is_blocker()]
            return False, f"{len(blockers)} unresolved critique blocker(s) remain"

        # Condition 4: Judge decision must be PASS (not FAIL or ABSTAIN)
        if verification_result.decision == "FAIL":
            return False, "Judge decision is FAIL"
        if verification_result.decision == "ABSTAIN":
            return False, "Judge decision is ABSTAIN (insufficient evidence)"

        # Condition 5: Quality evaluation passed
        if not quality.get("passed", False):
            return False, "quality evaluator has not passed"

        # Condition 6: Evidence sufficiency (optional enforcement)
        if self.require_evidence_sufficiency:
            if critique_result.evidence_sufficiency.level == "insufficient":
                return False, "evidence is insufficient — independent verification required"

        return True, "all_conditions_met"

    # -----------------------------------------------------------------------
    # Quality Evaluation
    # -----------------------------------------------------------------------

    def _evaluate_quality(
        self,
        workspace: str,
        verification_result: VerificationResult,
        critique_result: Any,
    ) -> Dict[str, Any]:
        """Merge Judge findings and critique findings into a single quality picture."""
        # Start from Judge findings
        judge_weaknesses = [
            {
                "id": f.id,
                "severity": f.severity,
                "description": f.description,
                "suggested_focus": f.suggested_focus,
                "evidence_level": "evidence_backed",  # judge findings are always backed
            }
            for f in verification_result.findings
        ]
        evaluation: Dict[str, Any] = {
            "source": "the_judge+critique",
            "score": float(verification_result.numeric_score),
            "threshold": self.quality_threshold,
            "weaknesses": judge_weaknesses,
        }

        # Merge critique blockers as quality weaknesses
        for cf in critique_result.get_open_findings():
            if cf.id not in {w.get("id") for w in evaluation["weaknesses"]}:
                evaluation["weaknesses"].append({
                    "id": cf.id,
                    "severity": cf.severity.value,
                    "description": cf.description,
                    "suggested_focus": cf.suggested_action,
                    "evidence_level": cf.evidence_level.value,
                })

        # Run optional external quality evaluator
        if self.quality_evaluator is not None:
            try:
                supplied = self.quality_evaluator(workspace, verification_result.to_dict())
                if not isinstance(supplied, Mapping):
                    raise TypeError("quality_evaluator must return a mapping")
                score = supplied.get("score", evaluation["score"])
                if not isinstance(score, (int, float)) or not 0 <= score <= 100:
                    raise ValueError("quality_evaluator score must be between 0 and 100")
                weaknesses = supplied.get("weaknesses", [])
                if not isinstance(weaknesses, list):
                    raise TypeError("quality_evaluator weaknesses must be a list")
                evaluation.update({
                    "source": supplied.get("source", "quality_evaluator"),
                    "score": float(score),
                    "weaknesses": [self._normalise_weakness(w) for w in weaknesses],
                    "passed": bool(supplied.get("passed", False)),
                })
            except Exception as exc:
                evaluation.update({
                    "source": "quality_evaluator_error",
                    "score": 0.0,
                    "weaknesses": [{
                        "id": "QUALITY-EVALUATOR-ERROR",
                        "severity": "high",
                        "description": str(exc),
                    }],
                    "passed": False,
                })

        if "passed" not in evaluation:
            # Passed only if score ≥ threshold AND no critique blockers remain
            evaluation["passed"] = (
                evaluation["score"] >= self.quality_threshold
                and not critique_result.has_blockers()
            )

        return evaluation

    # -----------------------------------------------------------------------
    # Feedback Construction
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_improvement_feedback(
        verification_feedback: Dict[str, Any],
        quality: Dict[str, Any],
        critique_result: Any,
        round_number: int,
        is_visual: bool,
        visual_eval: Dict[str, Any],
        audit_trail: AuditTrail,
    ) -> Dict[str, Any]:
        """Build the full feedback dict for the repair callback.

        Includes both Judge verification feedback and CritiqueEngine findings,
        ordered by priority (most critical, evidence-backed issues first).
        """
        feedback = copy.deepcopy(verification_feedback)
        feedback["quality_evaluation"] = quality

        # If Judge says PASS but quality/critique still has issues, signal IMPROVE
        if feedback["decision"] == "PASS":
            feedback["verification_decision"] = "PASS"
            feedback["decision"] = "IMPROVE"
            feedback["findings"] = quality["weaknesses"]

        # Independent critique (the main new signal)
        feedback["critique"] = critique_result.to_dict()

        # Round metadata
        feedback["round_number"] = round_number
        feedback["is_visual"] = is_visual
        feedback["visual_inspection"] = visual_eval

        # Audit trail history (so agent can see the full journey)
        feedback["audit_trail"] = audit_trail.to_dict()

        return feedback

    # -----------------------------------------------------------------------
    # Outcome Constructors
    # -----------------------------------------------------------------------

    def _complete(
        self,
        outcome: str,
        round_idx: int,
        verification_result: VerificationResult,
        quality: Dict[str, Any],
        audit_trail: AuditTrail,
    ) -> Dict[str, Any]:
        return {
            "outcome": outcome,
            "total_rounds": round_idx,
            "final_decision": verification_result.decision,
            "quality": quality,
            "history": self.rounds_history,
            "final_result": verification_result.to_dict(),
            "audit_trail": audit_trail.to_dict(),
        }

    def _abort(
        self,
        outcome: str,
        reason: str,
        round_idx: int,
        verification_result: VerificationResult,
        quality: Dict[str, Any],
        audit_trail: AuditTrail,
    ) -> Dict[str, Any]:
        result = self._complete(outcome, round_idx, verification_result, quality, audit_trail)
        result["reason"] = reason
        return result

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _normalise_weakness(weakness: Any) -> Dict[str, Any]:
        if isinstance(weakness, str):
            return {"id": "QUALITY", "severity": "medium", "description": weakness}
        if isinstance(weakness, Mapping) and isinstance(weakness.get("description"), str):
            return {
                "id": str(weakness.get("id", "QUALITY")),
                "severity": str(weakness.get("severity", "medium")),
                "description": weakness["description"],
                "suggested_focus": weakness.get("suggested_focus"),
            }
        raise TypeError("each quality weakness must be a string or mapping with a description")

    @staticmethod
    def _normalise_repair_result(result: RepairCallbackResult) -> Tuple[bool, Optional[str]]:
        if isinstance(result, Mapping):
            summary = result.get("summary")
            return bool(result.get("improved", False)), str(summary) if summary else None
        return bool(result), None

    def _compute_implementation_hash(self, workspace_path: str) -> str:
        """Hash source and deliverable assets, excluding caches and virtual envs."""
        hasher = hashlib.sha256()
        path = os.path.abspath(workspace_path)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                hasher.update(f.read())
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = sorted(
                    d for d in dirs if d not in self._IGNORED_DIRECTORIES
                )
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, path)
                    hasher.update(rel.encode("utf-8"))
                    with open(fpath, "rb") as f:
                        hasher.update(f.read())
        return hasher.hexdigest()[:16]


# Preserve backward-compatible alias
AgentImprovementLoop = AgentRepairLoop
