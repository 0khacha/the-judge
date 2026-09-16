from typing import Any, Dict, List, Optional
from the_judge.api import verify
from the_judge.core.decision import VerificationResult


class AgentAdapter:
    """Generic AI Coding Agent Integration Adapter.

    Serves as an isolation layer between AI coding agents and The Judge verification engine.
    Ensures agent receives actionable structured findings without exposing internal verifier
    attack strategies or hidden challenge implementation source code.
    """

    def __init__(self, name: str = "GenericCodingAgent"):
        self.name = name

    def verify_workspace(
        self,
        workspace: str,
        task_spec: Optional[Dict[str, Any]] = None,
        previous_evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run verification on target workspace and return structured agent findings.

        Args:
            workspace: Path to agent workspace directory or python source file.
            task_spec: Task specification contract (optional).
            previous_evidence: Snapshot from previous round for regression checking.

        Returns:
            Dictionary containing decision, actionable findings, trust profile, and provenance.
        """
        result: VerificationResult = verify(
            workspace=workspace,
            task_spec=task_spec,
            previous_evidence=previous_evidence,
        )

        return self.result_to_feedback(result)

    def result_to_feedback(self, result: VerificationResult) -> Dict[str, Any]:
        """Convert an existing result to safe agent-facing feedback.

        Repair loops reuse this result so one evaluation round produces one
        authoritative outcome instead of running the target a second time.
        """
        return {
            "decision": result.decision,
            "numeric_score": result.numeric_score,
            "findings": [f.to_dict() for f in result.findings],
            "trust_profile": result.trust_profile,
            "provenance": result.provenance,
            "blocking_issues": result.blocking_issues,
            "insufficient_notes": result.insufficient_notes,
            "runtime": {
                "duration_seconds": round(result.runtime_seconds, 3),
                "judge_version": "v4.0",
            },
        }

    def format_agent_prompt_feedback(self, adapter_result: Dict[str, Any]) -> str:
        """Format verification result into a clean text prompt feedback for the agent repair loop."""
        decision = adapter_result.get("decision", "UNKNOWN")
        lines = [
            "=== THE JUDGE VERIFICATION FEEDBACK ===",
            f"DECISION: {decision}",
        ]

        if decision == "PASS":
            lines.append("Verification succeeded. All behavioral properties and hard gates satisfied.")
            return "\n".join(lines)

        if decision == "IMPROVE":
            quality = adapter_result.get("quality_evaluation", {})
            lines.append("\nVerification passed, but the agreed quality bar has not been met yet.")
            lines.append(
                "Quality score: "
                f"{quality.get('score', 'unknown')} / {quality.get('threshold', 'unknown')}"
            )
            for weakness in quality.get("weaknesses", []):
                lines.append(f"  - {weakness.get('description', 'Unspecified quality weakness')}")
            lines.append("\nMake a concrete improvement, preserve verified behavior, and submit it for re-evaluation.")
            return "\n".join(lines)

        if decision == "FAIL":
            lines.append("\nThe Judge detected failures in your implementation:")
            for idx, finding in enumerate(adapter_result.get("findings", []), 1):
                lines.append(f"\nFinding #{idx} [{finding.get('id', 'F')}] ({finding.get('severity', 'high').upper()}):")
                lines.append(f"  Description    : {finding.get('description')}")
                if finding.get("property"):
                    lines.append(f"  Property       : {finding.get('property')}")
                if finding.get("observed"):
                    lines.append(f"  Observed       : {finding.get('observed')}")
                if finding.get("expected"):
                    lines.append(f"  Expected       : {finding.get('expected')}")
                if finding.get("suggested_focus"):
                    lines.append(f"  Suggested Focus: {finding.get('suggested_focus')}")

            if adapter_result.get("blocking_issues"):
                lines.append("\nBlocking Issues:")
                for issue in adapter_result["blocking_issues"]:
                    lines.append(f"  - {issue}")

        elif decision == "ABSTAIN":
            lines.append("\nThe Judge refused to grant PASS due to insufficient or unverified evidence:")
            for note in adapter_result.get("insufficient_notes", []):
                lines.append(f"  - {note}")
            lines.append("\nPlease provide independent unit tests or implementation code that allows verification.")

        lines.append("\nPlease repair your implementation addressing the above issues and submit again.")
        return "\n".join(lines)
