import copy
import hashlib
import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

from the_judge.api import verify
from the_judge.core.decision import VerificationResult
from the_judge.core.evidence import capture_evidence
from the_judge.integrations.agent_adapter import AgentAdapter


QualityEvaluator = Callable[[str, Dict[str, Any]], Dict[str, Any]]
RepairCallbackResult = Union[bool, Mapping[str, Any]]


class AgentRepairLoop:
    """Run evidence-led repair and quality-improvement rounds.

    A Judge ``PASS`` is a verification gate, but it is not necessarily the end
    of an improvement workflow. A caller can provide a quality evaluator for
    dimensions outside executable behavior, such as UX, accessibility, visual
    hierarchy, or maintainability. Its weaknesses are fed to the repair callback
    and every actual change is re-evaluated with regression evidence.
    """

    _IGNORED_DIRECTORIES = {
        ".git",
        ".hg",
        ".svn",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
    }

    def __init__(
        self,
        adapter: Optional[AgentAdapter] = None,
        max_rounds: int = 5,
        quality_threshold: float = 90.0,
        quality_evaluator: Optional[QualityEvaluator] = None,
    ):
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")
        if not 0 <= quality_threshold <= 100:
            raise ValueError("quality_threshold must be between 0 and 100")

        self.adapter = adapter or AgentAdapter()
        self.max_rounds = max_rounds
        self.quality_threshold = float(quality_threshold)
        self.quality_evaluator = quality_evaluator
        self.rounds_history: List[Dict[str, Any]] = []

    def run_repair_loop(
        self,
        workspace: str,
        agent_repair_func: Callable[[str, Dict[str, Any]], RepairCallbackResult],
        task_spec: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Improve a workspace until it passes verification and the quality bar."""
        from the_judge.core.visual_engine import VisualEngine

        self.rounds_history.clear()
        previous_evidence: Optional[Dict[str, Any]] = None

        visual_engine = VisualEngine(workspace)
        is_visual, target_visual_file = visual_engine.is_visual_workspace()
        artifacts_dir = (
            os.path.join(workspace, "_judge_visual")
            if os.path.isdir(workspace)
            else os.path.join(os.path.dirname(workspace), "_judge_visual")
        )
        previous_screenshot: Optional[str] = None

        for round_idx in range(1, self.max_rounds + 1):
            current_evidence = capture_evidence(workspace)
            implementation_hash = self._compute_implementation_hash(workspace)
            verification_result: VerificationResult = verify(
                workspace=workspace,
                task_spec=task_spec,
                previous_evidence=previous_evidence,
            )
            verification_feedback = self.adapter.result_to_feedback(verification_result)
            quality = self._evaluate_quality(workspace, verification_result)

            current_screenshot = None
            visual_eval = {"is_visual": False}

            if is_visual and target_visual_file:
                current_screenshot = visual_engine.capture_screenshot(
                    target_visual_file, round_idx, artifacts_dir
                )
                visual_eval = visual_engine.evaluate_visual_aspects(
                    target_visual_file, current_screenshot, previous_screenshot
                )
                previous_screenshot = current_screenshot

                # Merge visual weaknesses into quality evaluation if present
                for vis_w in visual_eval.get("weaknesses", []):
                    if not any(w.get("id") == vis_w.get("id") for w in quality["weaknesses"]):
                        quality["weaknesses"].append(vis_w)
                        # Slightly adjust score if visual defects found
                        quality["score"] = min(quality["score"], visual_eval.get("score", quality["score"]))

            round_record = {
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
                "findings": [finding.to_dict() for finding in verification_result.findings],
                "blocking_issues": verification_result.blocking_issues,
                "evidence_summary": {
                    "passed_tests": verification_result.provenance.get("passed_tests", 0),
                    "failed_tests": verification_result.provenance.get("failed_tests", 0),
                    "evidence_level": verification_result.provenance.get("evidence_level", 0),
                },
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self.rounds_history.append(round_record)

            if self._quality_target_met(verification_result, quality):
                return self._complete("PASS", round_idx, verification_result, quality)

            previous_evidence = copy.deepcopy(current_evidence)
            if round_idx == self.max_rounds:
                break

            feedback = self._build_improvement_feedback(verification_feedback, quality)
            feedback["is_visual"] = is_visual
            feedback["visual_inspection"] = visual_eval
            repair_before_hash = self._compute_implementation_hash(workspace)
            repair_result = agent_repair_func(workspace, feedback)
            repaired, repair_summary = self._normalise_repair_result(repair_result)
            round_record["repair"] = {
                "attempted": True,
                "reported_improved": repaired,
                "summary": repair_summary,
            }

            if not repaired:
                return self._abort(
                    "ABORTED",
                    "Agent repair callback returned False (unable to make an improvement).",
                    round_idx,
                    verification_result,
                    quality,
                )

            repair_after_hash = self._compute_implementation_hash(workspace)
            round_record["repair"]["workspace_changed"] = repair_before_hash != repair_after_hash
            if repair_before_hash == repair_after_hash:
                return self._abort(
                    "NO_MEANINGFUL_IMPROVEMENT",
                    "The repair callback reported success but did not change the workspace.",
                    round_idx,
                    verification_result,
                    quality,
                )

        last_round = self.rounds_history[-1]
        return {
            "outcome": "MAX_ROUNDS_EXCEEDED",
            "total_rounds": self.max_rounds,
            "final_decision": last_round["decision"],
            "quality": last_round["quality"],
            "history": self.rounds_history,
            "final_result": last_round,
        }

    def _evaluate_quality(
        self, workspace: str, verification_result: VerificationResult
    ) -> Dict[str, Any]:
        """Evaluate quality dimensions without allowing them to bypass Judge gates."""
        judge_weaknesses = [
            {
                "id": finding.id,
                "severity": finding.severity,
                "description": finding.description,
                "suggested_focus": finding.suggested_focus,
            }
            for finding in verification_result.findings
        ]
        evaluation: Dict[str, Any] = {
            "source": "the_judge",
            "score": float(verification_result.numeric_score),
            "threshold": self.quality_threshold,
            "weaknesses": judge_weaknesses,
        }

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
                evaluation.update(
                    {
                        "source": supplied.get("source", "quality_evaluator"),
                        "score": float(score),
                        "weaknesses": [self._normalise_weakness(item) for item in weaknesses],
                        "passed": bool(supplied.get("passed", False)),
                    }
                )
            except Exception as exc:
                evaluation.update(
                    {
                        "source": "quality_evaluator_error",
                        "score": 0.0,
                        "weaknesses": [
                            {
                                "id": "QUALITY-EVALUATOR-ERROR",
                                "severity": "high",
                                "description": str(exc),
                            }
                        ],
                        "passed": False,
                    }
                )

        if "passed" not in evaluation:
            evaluation["passed"] = (
                evaluation["score"] >= self.quality_threshold
                and not evaluation["weaknesses"]
            )
        return evaluation

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
    def _normalise_repair_result(result: RepairCallbackResult) -> tuple[bool, Optional[str]]:
        if isinstance(result, Mapping):
            summary = result.get("summary")
            return bool(result.get("improved", False)), str(summary) if summary else None
        return bool(result), None

    @staticmethod
    def _build_improvement_feedback(
        verification_feedback: Dict[str, Any], quality: Dict[str, Any]
    ) -> Dict[str, Any]:
        feedback = copy.deepcopy(verification_feedback)
        feedback["quality_evaluation"] = quality
        if feedback["decision"] == "PASS":
            feedback["verification_decision"] = "PASS"
            feedback["decision"] = "IMPROVE"
            feedback["findings"] = quality["weaknesses"]
        return feedback

    @staticmethod
    def _quality_target_met(
        verification_result: VerificationResult, quality: Dict[str, Any]
    ) -> bool:
        has_critical_weakness = any(
            weakness.get("severity", "").lower() == "critical"
            for weakness in quality["weaknesses"]
        )
        return (
            verification_result.decision == "PASS"
            and quality["score"] >= quality["threshold"]
            and bool(quality["passed"])
            and not has_critical_weakness
        )

    def _complete(
        self,
        outcome: str,
        round_idx: int,
        verification_result: VerificationResult,
        quality: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "outcome": outcome,
            "total_rounds": round_idx,
            "final_decision": verification_result.decision,
            "quality": quality,
            "history": self.rounds_history,
            "final_result": verification_result.to_dict(),
        }

    def _abort(
        self,
        outcome: str,
        reason: str,
        round_idx: int,
        verification_result: VerificationResult,
        quality: Dict[str, Any],
    ) -> Dict[str, Any]:
        result = self._complete(outcome, round_idx, verification_result, quality)
        result["reason"] = reason
        return result

    def _compute_implementation_hash(self, workspace_path: str) -> str:
        """Hash source and deliverable assets, excluding dependency and cache trees."""
        hasher = hashlib.sha256()
        path = os.path.abspath(workspace_path)
        if os.path.isfile(path):
            with open(path, "rb") as source_file:
                hasher.update(source_file.read())
        elif os.path.isdir(path):
            for root, directories, files in os.walk(path):
                directories[:] = sorted(
                    directory
                    for directory in directories
                    if directory not in self._IGNORED_DIRECTORIES
                )
                for file_name in sorted(files):
                    file_path = os.path.join(root, file_name)
                    relative_path = os.path.relpath(file_path, path)
                    hasher.update(relative_path.encode("utf-8"))
                    with open(file_path, "rb") as source_file:
                        hasher.update(source_file.read())
        return hasher.hexdigest()[:16]


# Clearer name for new integrations; preserve AgentRepairLoop for compatibility.
AgentImprovementLoop = AgentRepairLoop
