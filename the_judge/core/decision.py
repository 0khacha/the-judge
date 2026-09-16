from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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

    def to_dict(self) -> Dict[str, Any]:
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
    trust_profile: Dict[str, Any]
    findings: List[Finding]
    provenance: Dict[str, Any]
    blocking_issues: List[str]
    insufficient_notes: List[str]
    runtime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
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
                "judge_version": "v1.0.0"
            }
        }
