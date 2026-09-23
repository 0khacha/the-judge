from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Finding:
    id: str
    category: str  # "behavior", "collection", "type_check", "security", "regression"
    severity: str  # "blocking", "high", "medium", "low"
    description: str
    property_name: Optional[str] = None
    observed: Optional[str] = None
    expected: Optional[str] = None
    suggested_focus: Optional[str] = None

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "numeric_score": self.numeric_score,
            "trust_profile": self.trust_profile,
            "findings": [f.to_dict() for f in self.findings],
            "provenance": self.provenance,
            "blocking_issues": self.blocking_issues,
            "insufficient_notes": self.insufficient_notes,
            "runtime": {
                "duration_seconds": round(self.runtime_seconds, 3),
                "judge_version": "v1.0.0",
            },
        }
