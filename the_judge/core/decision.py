from dataclasses import dataclass, field
from typing import Any

from the_judge._version import __version__


@dataclass
class Finding:
    id: str
    category: str  # "behavior", "collection", "type_check", "security", "regression"
    severity: str  # "blocking", "high", "medium", "low"
    description: str
    property_name: str | None = None
    observed: str | None = None
    expected: str | None = None
    suggested_focus: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "property": self.property_name,
            "observed": self.observed,
            "expected": self.expected,
            "suggested_focus": self.suggested_focus,
        }


@dataclass
class VerificationResult:
    decision: str  # "PASS", "FAIL", "ABSTAIN"
    numeric_score: float
    trust_profile: dict[str, Any]
    findings: list[Finding]
    provenance: dict[str, Any]
    blocking_issues: list[str]
    insufficient_notes: list[str]
    runtime_seconds: float = 0.0
    # Numbered, machine-readable steps telling the agent what to do next.
    next_actions: list[dict[str, Any]] = field(default_factory=list)
    # Iteration bookkeeping when verification history is recorded (CLI default).
    loop: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "numeric_score": self.numeric_score,
            "trust_profile": self.trust_profile,
            "findings": [f.to_dict() for f in self.findings],
            "provenance": self.provenance,
            "blocking_issues": self.blocking_issues,
            "insufficient_notes": self.insufficient_notes,
            "next_actions": self.next_actions,
            "loop": self.loop,
            "runtime": {
                "duration_seconds": round(self.runtime_seconds, 3),
                "judge_version": f"v{__version__}",
            },
        }
