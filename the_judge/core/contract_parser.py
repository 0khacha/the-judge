import re
from typing import Any, Dict, List, Tuple

AMBIGUOUS_KEYWORDS = ["fast", "robust", "secure", "efficient", "optimal", "scalable", "clean"]


class ContractParser:
    """Natural Language Contract Parser & Requirement Extractor for The Judge v4.2."""

    def parse_natural_language_spec(self, spec_text: str) -> Dict[str, Any]:
        """Parses natural language task specifications into explicit and inferred requirement candidates.

        Args:
            spec_text: Natural language string describing task requirements.

        Returns:
            Dictionary containing extracted requirements, ambiguity warnings, and contradiction flags.
        """
        lines = [line.strip() for line in spec_text.splitlines() if line.strip()]
        requirements: List[Dict[str, Any]] = []
        ambiguities: List[str] = []
        contradictions: List[str] = []

        # 1. Parse sentences into requirement items
        sentences = re.split(r"(?<=[.!?])\s+", spec_text)
        req_idx = 1

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean or len(sentence_clean) < 10:
                continue

            # Check for ambiguity
            matched_ambig = [kw for kw in AMBIGUOUS_KEYWORDS if re.search(r"\b" + kw + r"\b", sentence_clean, re.I)]
            is_ambiguous = len(matched_ambig) > 0
            if is_ambiguous:
                ambiguities.append(f"Ambiguous requirement term '{matched_ambig[0]}' in sentence: '{sentence_clean}'")

            category = self._infer_category(sentence_clean)
            priority = "critical" if any(w in sentence_clean.lower() for w in ("must", "shall", "always", "required", "never")) else "important"

            requirements.append({
                "id": f"REQ-{req_idx:03d}",
                "description": sentence_clean,
                "category": category,
                "priority": priority,
                "provenance_type": "EXPLICIT_REQUIREMENT" if "must" in sentence_clean.lower() or "shall" in sentence_clean.lower() else "INFERRED_CANDIDATE",
                "ambiguous": is_ambiguous,
            })
            req_idx += 1

        # 2. Check for contradictions
        text_lower = spec_text.lower()
        if "retry all" in text_lower and "never retry" in text_lower:
            contradictions.append("CONTRADICTION DETECTED: Specification requests both 'retry all' and 'never retry'.")
        if "idempotent" in text_lower and "increment counter" in text_lower:
            contradictions.append("CONTRADICTION DETECTED: Specification requests idempotency alongside non-idempotent state increments.")

        return {
            "parsed_requirements": requirements,
            "ambiguities": ambiguities,
            "contradictions": contradictions,
            "has_contradictions": len(contradictions) > 0,
        }

    def _infer_category(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ("bound", "limit", "max", "min", "capacity", "threshold")):
            return "boundary"
        elif any(w in text_lower for w in ("ttl", "expire", "session", "state", "cache", "store")):
            return "state"
        elif any(w in text_lower for w in ("sanitize", "xss", "salt", "secret", "hash", "traversal", "security")):
            return "security"
        elif any(w in text_lower for w in ("raise", "error", "exception", "invalid", "reject")):
            return "error_handling"
        elif any(w in text_lower for w in ("idempotent", "repeated")):
            return "idempotency"
        return "functional"
