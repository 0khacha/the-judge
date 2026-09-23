import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PropertyMapping:
    property_id: str
    requirement_id: str
    property_name: str
    provenance: str  # "explicit_contract", "contract_derived", "interface_derived", "heuristic"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    justification: str
    status: str  # "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONFLICTING"


@dataclass
class RequirementCoverage:
    requirement_id: str
    description: str
    category: str  # "functional", "boundary", "state", "error_handling", "security", etc.
    priority: str  # "critical", "important", "optional"
    status: str  # "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONFLICTING"
    mapped_properties: list[PropertyMapping] = field(default_factory=list)
    unverified_reason: Optional[str] = None


class ContractEngine:
    """Contract-Aware Verification & Specification Coverage Engine for The Judge v4.2."""

    def __init__(self, task_spec: Optional[dict[str, Any]] = None):
        self.task_spec = task_spec or {}

    def evaluate_contract_coverage(
        self,
        ground_truth: dict[str, Any],
        agent_findings: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluates requirement specification coverage across explicit contract requirements.

        Returns:
            Dictionary containing requirement_coverages, coverage_summary, and critical_unverified_ids.
        """
        requirements_input = self.task_spec.get("requirements", [])
        if not requirements_input:
            # Infer baseline implicit requirements if no explicit contract provided
            requirements_input = self._infer_default_requirements(ground_truth)

        test_suite = ground_truth.get("test_suite", {})
        passed_tests = set(test_suite.get("passed_tests", []))
        failed_tests = set(test_suite.get("failed_tests", []))
        test_provenance = ground_truth.get("test_provenance", {})

        requirement_coverages: list[RequirementCoverage] = []

        for idx, req_data in enumerate(requirements_input, 1):
            req_id = req_data.get("id", f"REQ-{idx:03d}")
            desc = req_data.get("description", "")
            category = req_data.get("category", "functional")
            priority = req_data.get("priority", "critical")

            # Match executed tests to this requirement
            matched_passed = [t for t in passed_tests if self._matches_test(req_data, t)]
            matched_failed = [t for t in failed_tests if self._matches_test(req_data, t)]

            mapped_props: list[PropertyMapping] = []

            # Map passed test properties
            for p_test in matched_passed:
                prov = test_provenance.get(p_test, {}).get("source", "contract_derived")
                mapped_props.append(
                    PropertyMapping(
                        property_id=f"PROP-{p_test}",
                        requirement_id=req_id,
                        property_name=p_test,
                        provenance="explicit_contract"
                        if "task_spec" in self.task_spec
                        else "contract_derived",
                        confidence="HIGH" if prov == "judge_challenge_test" else "MEDIUM",
                        justification=f"Behavioral test '{p_test}' passed ground-truth execution.",
                        status="VERIFIED",
                    )
                )

            # Map failed test properties
            for f_test in matched_failed:
                mapped_props.append(
                    PropertyMapping(
                        property_id=f"PROP-{f_test}",
                        requirement_id=req_id,
                        property_name=f_test,
                        provenance="contract_derived",
                        confidence="HIGH",
                        justification=f"Behavioral test '{f_test}' failed ground-truth execution.",
                        status="CONFLICTING",
                    )
                )

            # Determine requirement status
            if matched_failed:
                status = "CONFLICTING"
                unverified_reason = f"Ground-truth test failed for {req_id}."
            elif matched_passed:
                has_challenge = any(
                    test_provenance.get(t, {}).get("source") == "judge_challenge_test"
                    for t in matched_passed
                )
                if has_challenge or len(matched_passed) >= 2:
                    status = "VERIFIED"
                    unverified_reason = None
                else:
                    status = "PARTIALLY_VERIFIED"
                    unverified_reason = "Only public workspace tests recorded; independent property challenges unverified."
            else:
                status = "UNVERIFIED"
                unverified_reason = (
                    f"No independent behavioral challenge was generated or executed for {req_id}."
                )

            requirement_coverages.append(
                RequirementCoverage(
                    requirement_id=req_id,
                    description=desc,
                    category=category,
                    priority=priority,
                    status=status,
                    mapped_properties=mapped_props,
                    unverified_reason=unverified_reason,
                )
            )

        # Calculate Coverage Statistics
        total_reqs = len(requirement_coverages)
        verified_cnt = sum(1 for r in requirement_coverages if r.status == "VERIFIED")
        partially_cnt = sum(1 for r in requirement_coverages if r.status == "PARTIALLY_VERIFIED")
        unverified_cnt = sum(1 for r in requirement_coverages if r.status == "UNVERIFIED")
        conflicting_cnt = sum(1 for r in requirement_coverages if r.status == "CONFLICTING")

        critical_reqs = [r for r in requirement_coverages if r.priority == "critical"]
        critical_total = len(critical_reqs)
        critical_verified = sum(1 for r in critical_reqs if r.status == "VERIFIED")
        critical_coverage_pct = (
            (critical_verified / critical_total * 100.0) if critical_total > 0 else 100.0
        )

        important_reqs = [r for r in requirement_coverages if r.priority == "important"]
        important_total = len(important_reqs)
        important_verified = sum(1 for r in important_reqs if r.status == "VERIFIED")
        important_coverage_pct = (
            (important_verified / important_total * 100.0) if important_total > 0 else 100.0
        )

        overall_coverage_pct = (verified_cnt / total_reqs * 100.0) if total_reqs > 0 else 0.0

        unverified_critical_ids = [
            r.requirement_id for r in critical_reqs if r.status in ("UNVERIFIED", "CONFLICTING")
        ]

        # Calculate Specification Escape Rate (% of failed ground-truth items caused by unverified requirements)
        spec_escape_rate_pct = 0.0
        if unverified_cnt > 0 and total_reqs > 0:
            spec_escape_rate_pct = round((unverified_cnt / total_reqs) * 100.0, 1)

        summary = {
            "total_requirements": total_reqs,
            "verified_count": verified_cnt,
            "partially_verified_count": partially_cnt,
            "unverified_count": unverified_cnt,
            "conflicting_count": conflicting_cnt,
            "critical_coverage_pct": round(critical_coverage_pct, 1),
            "important_coverage_pct": round(important_coverage_pct, 1),
            "overall_coverage_pct": round(overall_coverage_pct, 1),
            "specification_escape_rate_pct": spec_escape_rate_pct,
            "critical_unverified_ids": unverified_critical_ids,
        }

        return {
            "requirements": [self._format_coverage_dict(r) for r in requirement_coverages],
            "summary": summary,
        }

    def _infer_default_requirements(self, ground_truth: dict[str, Any]) -> list[dict[str, Any]]:
        test_suite = ground_truth.get("test_suite", {})
        all_tests = set(test_suite.get("passed_tests", []) + test_suite.get("failed_tests", []))
        reqs = []
        for idx, t in enumerate(sorted(all_tests), 1):
            reqs.append(
                {
                    "id": f"REQ-{idx:03d}",
                    "description": f"Behavioral verification of property {t}",
                    "category": "boundary"
                    if "boundary" in t
                    else ("security" if "security" in t or "xss" in t else "functional"),
                    "priority": "critical" if idx <= 2 else "important",
                }
            )
        if not reqs:
            reqs.append(
                {
                    "id": "REQ-001",
                    "description": "Functional contract implementation",
                    "category": "functional",
                    "priority": "critical",
                }
            )
        return reqs

    def _matches_test(self, req_data: dict[str, Any], test_name: str) -> bool:
        req_id = req_data.get("id", "")
        properties = req_data.get("properties", [])
        desc = req_data.get("description", "")

        test_lower = test_name.lower()
        req_lower = req_id.lower().replace("-", "_") if req_id else ""

        if req_lower and req_lower in test_lower:
            return True

        if test_lower in desc.lower() or test_lower.replace("test_", "") in desc.lower():
            return True

        if properties:
            for p in properties:
                p_clean = str(p).lower().replace("-", "_")
                if p_clean in test_lower:
                    return True
            return False

        desc_keywords = [
            w
            for w in re.findall(r"\w+", desc.lower())
            if len(w) >= 4
            and w
            not in (
                "should",
                "must",
                "returns",
                "system",
                "value",
                "level",
                "behavioral",
                "verification",
                "property",
            )
        ]
        matched_kw = [kw for kw in desc_keywords if kw in test_lower]
        return len(matched_kw) >= 1

    def _format_coverage_dict(self, req: RequirementCoverage) -> dict[str, Any]:
        return {
            "id": req.requirement_id,
            "description": req.description,
            "category": req.category,
            "priority": req.priority,
            "status": req.status,
            "mapped_properties": [
                {
                    "property_id": p.property_id,
                    "requirement_id": p.requirement_id,
                    "property_name": p.property_name,
                    "provenance": p.provenance,
                    "confidence": p.confidence,
                    "justification": p.justification,
                    "status": p.status,
                }
                for p in req.mapped_properties
            ],
            "unverified_reason": req.unverified_reason,
        }
