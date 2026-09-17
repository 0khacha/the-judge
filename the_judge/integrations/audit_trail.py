"""
AuditTrail — Immutable Per-Round History for The Judge Improvement Loop.

Philosophy
----------
Every round should produce an inspectable record that answers:

  > Why did the Judge decide the next version was better?

Not just:
  Round 1: 72  →  Round 2: 81  →  Round 3: 91

But rather:
  Round 1: Score 72, CONTRADICTED claim about error handling, 3 evidence-backed failures.
  Round 2: Fixed 2 test failures. Contradiction resolved. Score 81. Still missing edge-case tests.
  Round 3: Added boundary tests. Evidence now sufficient. No blockers. Score 91. STOP.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RoundRecord:
    """Complete record of a single improvement round."""

    round_number: int
    timestamp: str
    workspace_hash: str
    domain: str

    # --- Scores ------------------------------------------------------------
    previous_score: float
    new_score: float

    @property
    def score_delta(self) -> float:
        return round(self.new_score - self.previous_score, 2)

    # --- Verification (Judge) ----------------------------------------------
    decision: str
    judge_findings: List[Dict[str, Any]] = field(default_factory=list)
    blocking_issues: List[str] = field(default_factory=list)

    # --- Critique (independent) -------------------------------------------
    critique_findings: List[Dict[str, Any]] = field(default_factory=list)
    unverified_assumptions: List[str] = field(default_factory=list)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    agent_claims_unchecked: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    evidence_sufficiency: str = "unknown"        # "sufficient" | "partial" | "insufficient"
    has_blockers: bool = False
    skeptic_summary: str = ""

    # --- Evidence collected -----------------------------------------------
    evidence_summary: Dict[str, Any] = field(default_factory=dict)

    # --- Changes made this round ------------------------------------------
    improvement_actions: List[str] = field(default_factory=list)
    changes_summary: str = ""

    # --- Resolution tracking ---------------------------------------------
    resolved_finding_ids: List[str] = field(default_factory=list)
    new_finding_ids: List[str] = field(default_factory=list)
    remaining_findings: List[Dict[str, Any]] = field(default_factory=list)

    # --- Loop decision ----------------------------------------------------
    loop_decision: str = "continue"   # "continue" | "stop" | "abort"
    stop_reason: Optional[str] = None

    # --- Visual evidence (conditional) -----------------------------------
    screenshot_path: Optional[str] = None
    visual_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_number": self.round_number,
            "timestamp": self.timestamp,
            "workspace_hash": self.workspace_hash,
            "domain": self.domain,
            "scores": {
                "previous": self.previous_score,
                "new": self.new_score,
                "delta": self.score_delta,
            },
            "verification": {
                "decision": self.decision,
                "judge_findings": self.judge_findings,
                "blocking_issues": self.blocking_issues,
            },
            "critique": {
                "findings": self.critique_findings,
                "unverified_assumptions": self.unverified_assumptions,
                "contradictions": self.contradictions,
                "agent_claims_unchecked": self.agent_claims_unchecked,
                "missing_evidence": self.missing_evidence,
                "evidence_sufficiency": self.evidence_sufficiency,
                "has_blockers": self.has_blockers,
                "skeptic_summary": self.skeptic_summary,
            },
            "evidence_summary": self.evidence_summary,
            "changes": {
                "improvement_actions": self.improvement_actions,
                "summary": self.changes_summary,
            },
            "resolution": {
                "resolved_finding_ids": self.resolved_finding_ids,
                "new_finding_ids": self.new_finding_ids,
                "remaining_findings": self.remaining_findings,
            },
            "loop": {
                "decision": self.loop_decision,
                "stop_reason": self.stop_reason,
            },
            "visual": {
                "screenshot_path": self.screenshot_path,
                "visual_score": self.visual_score,
            },
        }


class AuditTrail:
    """Immutable per-round improvement history.

    Records not just score progression but *why* each round was better —
    which findings were resolved, what evidence was collected, which
    contradictions were cleared, and what the critique found.
    """

    def __init__(self) -> None:
        self._rounds: List[RoundRecord] = []

    # -----------------------------------------------------------------------
    # Recording
    # -----------------------------------------------------------------------

    def record_round(self, record: RoundRecord) -> None:
        """Append a completed round record."""
        self._rounds.append(record)

    # -----------------------------------------------------------------------
    # Accessors
    # -----------------------------------------------------------------------

    def get_history(self) -> List[RoundRecord]:
        return list(self._rounds)

    def get_score_progression(self) -> List[float]:
        return [r.new_score for r in self._rounds]

    def get_all_resolved_ids(self) -> List[str]:
        ids: List[str] = []
        for r in self._rounds:
            ids.extend(r.resolved_finding_ids)
        return ids

    def get_unresolved_findings(self) -> List[Dict[str, Any]]:
        """Return findings still open as of the last round."""
        if not self._rounds:
            return []
        return list(self._rounds[-1].remaining_findings)

    def initial_score(self) -> float:
        return self._rounds[0].previous_score if self._rounds else 0.0

    def final_score(self) -> float:
        return self._rounds[-1].new_score if self._rounds else 0.0

    def total_score_delta(self) -> float:
        return round(self.final_score() - self.initial_score(), 2)

    def screenshots(self) -> List[str]:
        return [r.screenshot_path for r in self._rounds if r.screenshot_path]

    # -----------------------------------------------------------------------
    # Serialisation
    # -----------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rounds": len(self._rounds),
            "initial_score": self.initial_score(),
            "final_score": self.final_score(),
            "total_score_delta": self.total_score_delta(),
            "rounds": [r.to_dict() for r in self._rounds],
        }

    def save_to_disk(self, output_dir: str) -> str:
        """Save the audit trail as JSON and a human-readable text summary.

        Returns path to the JSON file.
        """
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, "audit_trail.json")
        txt_path = os.path.join(output_dir, "audit_summary.txt")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.generate_text_summary())

        return json_path

    # -----------------------------------------------------------------------
    # Human-Readable Summary
    # -----------------------------------------------------------------------

    def generate_text_summary(self) -> str:
        lines: List[str] = []
        sep = "=" * 70
        lines.append(sep)
        lines.append("THE JUDGE — Improvement Audit Trail")
        lines.append(sep)
        lines.append(f"Total Rounds        : {len(self._rounds)}")
        lines.append(f"Initial Score       : {self.initial_score():.1f} / 100.0")
        lines.append(f"Final Score         : {self.final_score():.1f} / 100.0")
        delta = self.total_score_delta()
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        lines.append(f"Total Score Delta   : {delta_str}")
        lines.append("")

        for r in self._rounds:
            lines.append("-" * 70)
            lines.append(f"ROUND {r.round_number} — {r.timestamp}")
            lines.append(f"  Domain         : {r.domain}")
            lines.append(f"  Decision       : {r.decision}")
            d_str = f"+{r.score_delta:.1f}" if r.score_delta >= 0 else f"{r.score_delta:.1f}"
            lines.append(f"  Score          : {r.previous_score:.1f} → {r.new_score:.1f} ({d_str})")
            lines.append(f"  Evidence       : {r.evidence_sufficiency}")
            lines.append(f"  Blockers       : {'YES' if r.has_blockers else 'none'}")

            if r.skeptic_summary:
                lines.append(f"  Critique       : {r.skeptic_summary}")

            if r.contradictions:
                lines.append(f"  Contradictions : {len(r.contradictions)}")
                for c in r.contradictions[:2]:
                    lines.append(f"    • {c.get('description', '')[:100]}")

            if r.resolved_finding_ids:
                lines.append(f"  Resolved       : {', '.join(r.resolved_finding_ids[:5])}")

            if r.improvement_actions:
                lines.append(f"  Improvements   : {len(r.improvement_actions)} action(s)")
                for action in r.improvement_actions[:3]:
                    lines.append(f"    • {action[:120]}")

            if r.screenshot_path:
                rel = os.path.basename(r.screenshot_path)
                lines.append(f"  Screenshot     : {rel}")

            lines.append(f"  Loop Decision  : {r.loop_decision.upper()}"
                         + (f" — {r.stop_reason}" if r.stop_reason else ""))
            lines.append("")

        lines.append(sep)
        unresolved = self.get_unresolved_findings()
        if unresolved:
            lines.append(f"UNRESOLVED FINDINGS ({len(unresolved)}):")
            for f in unresolved[:5]:
                sev = f.get("severity", "?").upper()
                ev = f.get("evidence_level", "?")
                desc = f.get("description", "")[:100]
                lines.append(f"  [{sev}][{ev}] {desc}")
        else:
            lines.append("No unresolved findings remaining.")
        lines.append(sep)

        return "\n".join(lines)
