"""
CritiqueEngine — Independent Adversarial Critique for The Judge.

Philosophy
----------
The agent that produces work cannot be trusted to judge its own work alone.
This engine acts as an independent adversarial layer that:

  1. Independently asks 11 skeptical questions about the work.
  2. Classifies every finding by evidence level (EVIDENCE_BACKED, OBSERVED,
     UNVERIFIED_ASSUMPTION, AGENT_CLAIM, CONTRADICTED).
  3. Assigns severity (CRITICAL → INFO) independently of evidence level.
  4. Detects direct contradictions between agent claims and ground-truth evidence.
  5. Identifies unverified assumptions baked into code.
  6. Assesses evidence sufficiency for the project domain.
  7. Produces a prioritised improvement plan.

The agent's explanation is NEVER treated as proof.
"""

import ast
import contextlib
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Evidence & Finding Types
# ---------------------------------------------------------------------------


class EvidenceLevel(str, Enum):
    """How strongly a finding is supported by external, independent evidence."""

    EVIDENCE_BACKED = "evidence_backed"
    """Concrete evidence exists: test failure, log output, benchmark regression."""

    OBSERVED = "observed"
    """Directly visible in the artefact without running it, but not formally tested."""

    UNVERIFIED_ASSUMPTION = "unverified_assumption"
    """The agent relies on something that has not been demonstrated."""

    AGENT_CLAIM = "agent_claim"
    """The agent explicitly asserts something with no independent backing."""

    CONTRADICTED = "contradicted"
    """The agent claims X; available evidence demonstrates not-X."""


class FindingSeverity(str, Enum):
    """Impact severity — independent of how the finding was discovered."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingResolution(str, Enum):
    """Current resolution state of a finding."""

    OPEN = "open"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"  # Known, won't fix (deliberate decision)
    INVALIDATED = "invalidated"  # Finding was incorrect


class ProjectDomain(str, Enum):
    SOFTWARE_LIBRARY = "software_library"
    WEB_APP_OR_UI = "web_app_or_ui"
    DATA_SCIENCE = "data_science"
    CLI_SCRIPT = "cli_script"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass
class CritiqueFinding:
    """A single finding from the adversarial critique.

    Evidence level and severity are separate dimensions:
      - EVIDENCE_BACKED + LOW does NOT automatically block the loop.
      - CONTRADICTED + CRITICAL always blocks the loop.
    """

    id: str
    question: str  # Which of the 11 skeptical questions this answers
    description: str
    evidence_level: EvidenceLevel
    severity: FindingSeverity
    resolution: FindingResolution = FindingResolution.OPEN
    evidence_refs: list[str] = field(default_factory=list)
    suggested_action: str = ""
    agent_claim: Optional[str] = None  # The claim being contradicted (CONTRADICTED only)

    def is_blocker(self) -> bool:
        """Return True when this finding must be resolved before the loop may stop.

        Blocker criteria:
          - CONTRADICTED + CRITICAL or HIGH
          - EVIDENCE_BACKED + CRITICAL
          - EVIDENCE_BACKED + HIGH
        Non-blocking examples:
          - EVIDENCE_BACKED + LOW
          - OBSERVED + MEDIUM
          - AGENT_CLAIM + any severity
        """
        if self.resolution != FindingResolution.OPEN:
            return False
        if self.evidence_level == EvidenceLevel.CONTRADICTED:
            return self.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)
        if self.evidence_level == EvidenceLevel.EVIDENCE_BACKED:
            return self.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "description": self.description,
            "evidence_level": self.evidence_level.value,
            "severity": self.severity.value,
            "resolution": self.resolution.value,
            "evidence_refs": self.evidence_refs,
            "suggested_action": self.suggested_action,
            "agent_claim": self.agent_claim,
            "is_blocker": self.is_blocker(),
        }


@dataclass
class EvidenceSufficiency:
    level: str  # "sufficient" | "partial" | "insufficient"
    independent_tests: int
    agent_controlled_tests: int
    has_contradictions: bool
    reasons: list[str]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "independent_tests": self.independent_tests,
            "agent_controlled_tests": self.agent_controlled_tests,
            "has_contradictions": self.has_contradictions,
            "reasons": self.reasons,
            "summary": self.summary,
        }


@dataclass
class CritiqueResult:
    """Complete output of one adversarial critique round."""

    domain: str
    findings: list[CritiqueFinding]
    unverified_assumptions: list[str]
    contradictions: list[dict[str, Any]]
    missing_evidence: list[str]
    agent_claims_unchecked: list[str]
    evidence_sufficiency: EvidenceSufficiency
    skeptic_summary: str
    improvement_priority: list[CritiqueFinding]  # Open findings, most critical first

    # ---- Convenience ---------------------------------------------------

    def has_blockers(self) -> bool:
        return any(f.is_blocker() for f in self.findings)

    def get_open_findings(self) -> list[CritiqueFinding]:
        return [f for f in self.findings if f.resolution == FindingResolution.OPEN]

    def get_open_by_severity(self, severity: FindingSeverity) -> list[CritiqueFinding]:
        return [
            f
            for f in self.findings
            if f.resolution == FindingResolution.OPEN and f.severity == severity
        ]

    def to_dict(self) -> dict[str, Any]:
        open_count = len(self.get_open_findings())
        blocker_count = sum(1 for f in self.findings if f.is_blocker())
        return {
            "domain": self.domain,
            "findings": [f.to_dict() for f in self.findings],
            "unverified_assumptions": self.unverified_assumptions,
            "contradictions": self.contradictions,
            "missing_evidence": self.missing_evidence,
            "agent_claims_unchecked": self.agent_claims_unchecked,
            "evidence_sufficiency": self.evidence_sufficiency.to_dict(),
            "skeptic_summary": self.skeptic_summary,
            "improvement_priority": [f.to_dict() for f in self.improvement_priority],
            "has_blockers": self.has_blockers(),
            "open_findings_count": open_count,
            "blocker_count": blocker_count,
        }


# ---------------------------------------------------------------------------
# Critique Engine
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Module-level shared constants (referenced from CritiqueEngine and repair_loop)
# ---------------------------------------------------------------------------

_IGNORED_DIRS: frozenset = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
    }
)


class CritiqueEngine:
    """Adversarial critique engine — the independent skeptical evaluator.

    The 11 Skeptical Questions Asked Each Round
    -------------------------------------------
    1. What is wrong with this work?
    2. What is weak?
    3. What is missing?
    4. What has not been demonstrated?
    5. What assumptions are being made?
    6. What could fail in practice?
    7. What would a skeptical expert challenge?
    8. What claims are unsupported?
    9. What evidence contradicts the agent?
    10. What should be tested next?
    11. What improvement would have the highest impact?

    Evidence Level vs Severity
    --------------------------
    These are separate dimensions. EVIDENCE_BACKED + LOW does not block the loop.
    CONTRADICTED + CRITICAL always blocks the loop. See CritiqueFinding.is_blocker().
    """

    SKEPTICAL_QUESTIONS: list[str] = [
        "What is wrong with this work?",
        "What is weak?",
        "What is missing?",
        "What has not been demonstrated?",
        "What assumptions are being made?",
        "What could fail in practice?",
        "What would a skeptical expert challenge?",
        "What claims are unsupported?",
        "What evidence contradicts the agent?",
        "What should be tested next?",
        "What improvement would have the highest impact?",
    ]

    # Reuse the module-level constant (avoids duplicating the frozenset)
    _IGNORED_DIRS = _IGNORED_DIRS

    _CLAIM_PATTERN = re.compile(
        r"\b(always\s+returns?|never\s+raises?|guaranteed|ensures?|handles?\s+all"
        r"|all\s+(cases?|edge|inputs?)|completely|perfectly\s+(safe|secure)|"
        r"fully\s+(tested|covered)|zero\s+(vulnerabilities?|bugs?|errors?))\b",
        re.IGNORECASE,
    )

    _TODO_PATTERN = re.compile(r"#\s*(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)

    # -----------------------------------------------------------------------
    # Domain Classification
    # -----------------------------------------------------------------------

    def classify_domain(self, workspace: str) -> ProjectDomain:
        """Classify the project domain from workspace structure and content."""
        workspace = os.path.abspath(workspace)

        if os.path.isfile(workspace):
            return self._classify_single_file(workspace)

        html_count = js_count = py_count = ipynb_count = md_count = 0
        has_cli = has_data_science = has_web_framework = False

        for root, dirs, files in os.walk(workspace):
            dirs[:] = sorted(d for d in dirs if d not in self._IGNORED_DIRS)
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".html", ".htm"):
                    html_count += 1
                elif ext in (".js", ".ts", ".jsx", ".tsx", ".vue", ".svelte"):
                    js_count += 1
                elif ext == ".py":
                    py_count += 1
                    fpath = os.path.join(root, fname)
                    try:
                        content = open(fpath, encoding="utf-8", errors="ignore").read(4096).lower()
                        if any(kw in content for kw in ("argparse", "click", "typer", "__main__")):
                            has_cli = True
                        if any(
                            kw in content
                            for kw in ("pandas", "numpy", "sklearn", "torch", "tensorflow", "keras")
                        ):
                            has_data_science = True
                        if any(
                            kw in content
                            for kw in (
                                "flask",
                                "fastapi",
                                "django",
                                "streamlit",
                                "gradio",
                                "aiohttp",
                            )
                        ):
                            has_web_framework = True
                    except Exception:
                        pass
                elif ext == ".ipynb":
                    ipynb_count += 1
                elif ext in (".md", ".rst"):
                    md_count += 1

        if html_count > 0 or js_count > 2 or has_web_framework:
            return ProjectDomain.WEB_APP_OR_UI
        if ipynb_count > 0 or has_data_science:
            return ProjectDomain.DATA_SCIENCE
        if has_cli and py_count <= 5:
            return ProjectDomain.CLI_SCRIPT
        if md_count > 0 and py_count == 0:
            return ProjectDomain.DOCUMENTATION
        if py_count > 0:
            return ProjectDomain.SOFTWARE_LIBRARY
        return ProjectDomain.UNKNOWN

    def _classify_single_file(self, filepath: str) -> ProjectDomain:
        ext = os.path.splitext(filepath)[1].lower()
        if ext in (".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte"):
            return ProjectDomain.WEB_APP_OR_UI
        if ext in (".md", ".rst"):
            return ProjectDomain.DOCUMENTATION
        if ext == ".ipynb":
            return ProjectDomain.DATA_SCIENCE
        if ext == ".py":
            try:
                content = open(filepath, encoding="utf-8", errors="ignore").read(4096).lower()
                if any(k in content for k in ("argparse", "click", "__main__")):
                    return ProjectDomain.CLI_SCRIPT
                if any(k in content for k in ("pandas", "sklearn", "torch")):
                    return ProjectDomain.DATA_SCIENCE
            except Exception:
                pass
        return ProjectDomain.SOFTWARE_LIBRARY

    # -----------------------------------------------------------------------
    # Main Critique Entry Point
    # -----------------------------------------------------------------------

    def critique(
        self,
        workspace: str,
        verification_result: Any,
        ground_truth: dict[str, Any],
        previous_round: Optional[dict[str, Any]] = None,
    ) -> CritiqueResult:
        """Run a full independent adversarial critique of the workspace.

        Args:
            workspace: Path to the workspace directory or source file.
            verification_result: VerificationResult from the Judge (not trusted as evidence).
            ground_truth: Raw evidence dict from capture_evidence().
            previous_round: Round record from the previous iteration for comparison.

        Returns:
            CritiqueResult with classified findings, contradictions, and prioritised plan.
        """
        workspace = os.path.abspath(workspace)
        domain = self.classify_domain(workspace)

        id_counter = [0]

        def next_id(prefix: str) -> str:
            id_counter[0] += 1
            return f"CRIT-{prefix}-{id_counter[0]:03d}"

        findings: list[CritiqueFinding] = []

        # Build a shared source-file cache so downstream passes don't re-read from disk.
        # _scan_code_for_observed_issues and _identify_unverified_assumptions both need
        # the same file contents — reading once reduces disk I/O by ~50%.
        py_files = self._collect_source_files(workspace, (".py",), exclude_tests=True)
        source_cache: dict[str, str] = {}
        for fpath in py_files:
            with contextlib.suppress(Exception):
                source_cache[fpath] = open(fpath, encoding="utf-8", errors="ignore").read()

        # --- Q1 / Q9: What is wrong? Evidence-backed test failures -----------
        findings.extend(self._findings_from_test_failures(ground_truth, next_id))

        # --- Q9: Contradictions — agent claims vs evidence -------------------
        contradictions = self._detect_contradictions(ground_truth, verification_result)
        for contra in contradictions:
            findings.append(
                CritiqueFinding(
                    id=next_id("CONTRA"),
                    question="What evidence contradicts the agent?",
                    description=contra["description"],
                    evidence_level=EvidenceLevel.CONTRADICTED,
                    severity=FindingSeverity.CRITICAL
                    if contra.get("material", False)
                    else FindingSeverity.HIGH,
                    evidence_refs=contra.get("evidence_refs", []),
                    suggested_action=contra.get(
                        "suggested_action", "Resolve the contradiction between claim and evidence."
                    ),
                    agent_claim=contra.get("claim"),
                )
            )

        # --- Q3 / Q4 / Q6 / Q7: Observed issues in source code ---------------
        observed = self._scan_code_for_observed_issues(workspace, domain, source_cache=source_cache)
        findings.extend(observed)

        # --- Q5: Unverified assumptions ---------------------------------------
        assumptions = self._identify_unverified_assumptions(
            workspace, ground_truth, domain, source_cache=source_cache
        )

        # --- Q3 / Q10: Missing evidence for this domain ----------------------
        missing_evidence = self._assess_missing_evidence(workspace, ground_truth, domain)
        for missing in missing_evidence:
            findings.append(
                CritiqueFinding(
                    id=next_id("MISS"),
                    question="What is missing?",
                    description=missing,
                    evidence_level=EvidenceLevel.OBSERVED,
                    severity=FindingSeverity.MEDIUM,
                    suggested_action=f"Provide the missing coverage: {missing}",
                )
            )

        # --- Q8: Agent claims with no independent backing --------------------
        unchecked_claims = self._find_unchecked_agent_claims(ground_truth, verification_result)

        # Evidence sufficiency assessment
        evidence_sufficiency = self._assess_evidence_sufficiency(ground_truth, contradictions)

        # Prioritise open findings
        priority_order = self._prioritize_findings(findings)

        # Skeptic summary
        skeptic_summary = self._generate_skeptic_summary(
            domain,
            findings,
            contradictions,
            missing_evidence,
            evidence_sufficiency,
        )

        return CritiqueResult(
            domain=domain.value,
            findings=findings,
            unverified_assumptions=assumptions,
            contradictions=contradictions,
            missing_evidence=missing_evidence,
            agent_claims_unchecked=unchecked_claims,
            evidence_sufficiency=evidence_sufficiency,
            skeptic_summary=skeptic_summary,
            improvement_priority=priority_order,
        )

    # -----------------------------------------------------------------------
    # Finding Generators
    # -----------------------------------------------------------------------

    def _findings_from_test_failures(
        self,
        ground_truth: dict[str, Any],
        next_id,
    ) -> list[CritiqueFinding]:
        findings = []
        test_suite = ground_truth.get("test_suite", {})
        failed = test_suite.get("failed_tests", [])
        errors: dict[str, Any] = test_suite.get("errors", {})

        for ft in failed:
            err = errors.get(ft, "")
            err_snippet = (str(err)[:200] + "…") if len(str(err)) > 200 else str(err)
            findings.append(
                CritiqueFinding(
                    id=next_id("FAIL"),
                    question="What is wrong with this work?",
                    description=f"Test '{ft}' failed in ground-truth sandbox execution.",
                    evidence_level=EvidenceLevel.EVIDENCE_BACKED,
                    severity=FindingSeverity.HIGH,
                    evidence_refs=[ft],
                    suggested_action=(
                        f"Fix the failing test '{ft}'."
                        + (f" Error: {err_snippet}" if err_snippet else "")
                    ),
                )
            )
        return findings

    # -----------------------------------------------------------------------
    # Contradiction Detection
    # -----------------------------------------------------------------------

    def _detect_contradictions(
        self,
        ground_truth: dict[str, Any],
        verification_result: Any,
    ) -> list[dict[str, Any]]:
        """Find places where agent/code claims conflict with ground-truth evidence."""
        contradictions = []
        test_suite = ground_truth.get("test_suite", {})
        set(test_suite.get("passed_tests", []))
        set(test_suite.get("failed_tests", []))

        # 1. Tampered challenge file
        manifest = ground_truth.get("challenge_manifest", {})
        if manifest.get("file_tampered", False):
            contradictions.append(
                {
                    "claim": "Challenge test file integrity",
                    "description": (
                        "Challenge test file hash mismatch — file was modified during execution. "
                        "This directly contradicts the expectation of unmodified test integrity."
                    ),
                    "evidence_refs": ["challenge_manifest.file_tampered"],
                    "material": True,
                    "suggested_action": "Do not modify Judge-synthesised challenge test files during execution.",
                }
            )

        # 2. Missing expected challenges
        missing_challenges = manifest.get("missing_challenges", [])
        if missing_challenges:
            contradictions.append(
                {
                    "claim": "All expected challenge tests were executed",
                    "description": (
                        f"{len(missing_challenges)} expected challenge test(s) were not executed: "
                        + ", ".join(missing_challenges[:5])
                    ),
                    "evidence_refs": ["challenge_manifest.missing_challenges"],
                    "material": True,
                    "suggested_action": "Ensure synthesised challenge tests are collected and executed without interference.",
                }
            )

        # 3. Score vs evidence level mismatch
        trust_profile = getattr(verification_result, "trust_profile", {}) or {}
        evidence_level = trust_profile.get("evidence_level", 0)
        numeric_score = getattr(verification_result, "numeric_score", 0.0) or 0.0
        decision = getattr(verification_result, "decision", "") or ""

        if numeric_score > 80.0 and evidence_level < 2 and decision != "PASS":
            contradictions.append(
                {
                    "claim": f"High quality score implies verified quality ({numeric_score}/100)",
                    "description": (
                        f"Score is {numeric_score}/100 but evidence level is {evidence_level}/3. "
                        "A high score without sufficient independent evidence does not indicate quality."
                    ),
                    "evidence_refs": [f"evidence_level={evidence_level}", f"score={numeric_score}"],
                    "material": True,
                    "suggested_action": (
                        "Provide independent tests so the score reflects verified, not assumed, quality."
                    ),
                }
            )

        # 4. Regression: previously passing test now fails
        if hasattr(verification_result, "blocking_issues"):
            for issue in verification_result.blocking_issues or []:
                if "REGRESSION DETECTED" in issue:
                    contradictions.append(
                        {
                            "claim": "No regressions introduced",
                            "description": issue,
                            "evidence_refs": ["score_engine.regression"],
                            "material": True,
                            "suggested_action": "Fix the regression — a test that previously passed now fails.",
                        }
                    )

        return contradictions

    # -----------------------------------------------------------------------
    # Code Scanning (Observed Issues)
    # -----------------------------------------------------------------------

    def _scan_code_for_observed_issues(
        self,
        workspace: str,
        domain: ProjectDomain,
        source_cache: Optional[dict[str, str]] = None,
    ) -> list[CritiqueFinding]:
        """Scan source files for directly observable weaknesses.

        Args:
            source_cache: Optional pre-read {path: content} mapping. When provided,
                files are not re-read from disk (avoids duplicate I/O with critique()).
        """
        findings: list[CritiqueFinding] = []
        obs_idx = [500]

        def obs_id(tag: str = "OBS") -> str:
            obs_idx[0] += 1
            return f"CRIT-{tag}-{obs_idx[0]:03d}"

        # Use cached contents if available; otherwise fall back to reading from disk.
        if source_cache is not None:
            for fpath, content in source_cache.items():
                rel = os.path.relpath(fpath, workspace)
                findings.extend(self._analyse_python_file(content, rel, obs_id, domain))
        else:
            py_files = self._collect_source_files(workspace, (".py",), exclude_tests=True)
            for fpath in py_files:
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                    rel = os.path.relpath(fpath, workspace)
                    findings.extend(self._analyse_python_file(content, rel, obs_id, domain))
                except Exception:
                    pass

        if domain == ProjectDomain.WEB_APP_OR_UI:
            html_files = self._collect_source_files(workspace, (".html", ".htm"))
            for fpath in html_files:
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read()
                    rel = os.path.relpath(fpath, workspace)
                    findings.extend(self._analyse_html_file(content, rel, obs_id))
                except Exception:
                    pass

        return findings

    def _analyse_python_file(
        self,
        content: str,
        rel_path: str,
        next_id,
        domain: ProjectDomain,
    ) -> list[CritiqueFinding]:
        findings: list[CritiqueFinding] = []

        # Parse AST — syntax errors are EVIDENCE_BACKED CRITICAL
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            findings.append(
                CritiqueFinding(
                    id=next_id("SYN"),
                    question="What is wrong with this work?",
                    description=f"Syntax error in {rel_path}: {exc}",
                    evidence_level=EvidenceLevel.EVIDENCE_BACKED,
                    severity=FindingSeverity.CRITICAL,
                    evidence_refs=[rel_path],
                    suggested_action=f"Fix the syntax error at line {exc.lineno} of {rel_path}.",
                )
            )
            return findings

        # Silent broad exception handlers
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                is_broad = node.type is None or (
                    isinstance(node.type, ast.Name) and node.type.id == "Exception"
                )
                is_silent = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                if is_broad and is_silent:
                    findings.append(
                        CritiqueFinding(
                            id=next_id(),
                            question="What could fail in practice?",
                            description=(
                                f"Silent broad exception handler in {rel_path} (line {node.lineno}) "
                                "— errors are swallowed silently."
                            ),
                            evidence_level=EvidenceLevel.OBSERVED,
                            severity=FindingSeverity.MEDIUM,
                            evidence_refs=[f"{rel_path}:L{node.lineno}"],
                            suggested_action=(
                                "Replace the silent `except` with specific exception types "
                                "or at minimum log the error before suppressing it."
                            ),
                        )
                    )

        # TODO / FIXME markers
        seen_todos: set = set()
        for i, line in enumerate(content.splitlines(), 1):
            m = self._TODO_PATTERN.search(line)
            if m:
                tag = m.group(1).upper()
                key = f"{rel_path}:{i}"
                if key not in seen_todos:
                    seen_todos.add(key)
                    findings.append(
                        CritiqueFinding(
                            id=next_id(),
                            question="What is missing?",
                            description=(f"{tag} in {rel_path}:{i} — {line.strip()[:120]}"),
                            evidence_level=EvidenceLevel.OBSERVED,
                            severity=FindingSeverity.LOW,
                            evidence_refs=[f"{rel_path}:L{i}"],
                            suggested_action=f"Address the {tag} or document it as a known accepted limitation.",
                        )
                    )

        # Assertive claims in docstrings (AGENT_CLAIM)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                doc = ast.get_docstring(node)
                if doc:
                    m = self._CLAIM_PATTERN.search(doc)
                    if m:
                        findings.append(
                            CritiqueFinding(
                                id=next_id(),
                                question="What claims are unsupported?",
                                description=(
                                    f"Assertive claim in docstring of '{node.name}' ({rel_path}): "
                                    f"'...{m.group(0)}...' — is this verified by independent tests?"
                                ),
                                evidence_level=EvidenceLevel.AGENT_CLAIM,
                                severity=FindingSeverity.LOW,
                                evidence_refs=[f"{rel_path}:{node.name}"],
                                suggested_action=(
                                    f"Add a test that specifically verifies the claim "
                                    f"'{m.group(0)}' in '{node.name}'."
                                ),
                            )
                        )

        # Missing type annotations on public APIs
        unannotated: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                missing_params = [
                    a.arg for a in node.args.args if a.annotation is None and a.arg != "self"
                ]
                if missing_params or node.returns is None:
                    unannotated.append(node.name)

        if len(unannotated) > 2:
            findings.append(
                CritiqueFinding(
                    id=next_id(),
                    question="What assumptions are being made?",
                    description=(
                        f"{len(unannotated)} public function(s) in {rel_path} lack type annotations: "
                        + ", ".join(unannotated[:5])
                        + ("…" if len(unannotated) > 5 else "")
                    ),
                    evidence_level=EvidenceLevel.OBSERVED,
                    severity=FindingSeverity.LOW,
                    evidence_refs=[rel_path],
                    suggested_action=(
                        "Add type annotations to clarify expected inputs and return types, "
                        "reducing implicit assumptions."
                    ),
                )
            )

        return findings

    def _analyse_html_file(self, content: str, rel_path: str, next_id) -> list[CritiqueFinding]:
        findings: list[CritiqueFinding] = []
        cl = content.lower()

        # Images without alt text
        img_count = cl.count("<img")
        alt_count = cl.count("alt=")
        if img_count > 0 and alt_count < img_count:
            findings.append(
                CritiqueFinding(
                    id=next_id("A11Y"),
                    question="What would a skeptical expert challenge?",
                    description=(
                        f"{img_count - alt_count} image(s) in {rel_path} appear to lack alt attributes — accessibility failure."
                    ),
                    evidence_level=EvidenceLevel.OBSERVED,
                    severity=FindingSeverity.MEDIUM,
                    evidence_refs=[rel_path],
                    suggested_action="Add descriptive alt attributes to all <img> elements.",
                )
            )

        # Password in text field
        if "password" in cl and 'type="text"' in cl:
            findings.append(
                CritiqueFinding(
                    id=next_id("SEC"),
                    question="What could fail in practice?",
                    description=f"Possible password field using type='text' in {rel_path} — credentials exposed.",
                    evidence_level=EvidenceLevel.OBSERVED,
                    severity=FindingSeverity.HIGH,
                    evidence_refs=[rel_path],
                    suggested_action="Use type='password' for all password input fields.",
                )
            )

        # Missing viewport meta
        if "<html" in cl and "viewport" not in cl:
            findings.append(
                CritiqueFinding(
                    id=next_id("RESP"),
                    question="What is missing?",
                    description=f"No viewport meta tag in {rel_path} — page will not respond correctly on mobile.",
                    evidence_level=EvidenceLevel.OBSERVED,
                    severity=FindingSeverity.LOW,
                    evidence_refs=[rel_path],
                    suggested_action='Add <meta name="viewport" content="width=device-width, initial-scale=1.0">.',
                )
            )

        return findings

    # -----------------------------------------------------------------------
    # Unverified Assumptions
    # -----------------------------------------------------------------------

    def _identify_unverified_assumptions(
        self,
        workspace: str,
        ground_truth: dict[str, Any],
        domain: ProjectDomain,
        source_cache: Optional[dict[str, str]] = None,
    ) -> list[str]:
        """Find assumptions embedded in code that have not been tested."""
        assumptions: list[str] = []
        passed = set(ground_truth.get("test_suite", {}).get("passed_tests", []))

        # Assumption: valid inputs only (no None/empty/edge case tests)
        if domain in (ProjectDomain.SOFTWARE_LIBRARY, ProjectDomain.CLI_SCRIPT):
            none_tests = [
                t for t in passed if any(k in t.lower() for k in ("none", "null", "empty", "nil"))
            ]
            if not none_tests and passed:
                assumptions.append(
                    "No tests verify behaviour with None, empty, or null inputs — "
                    "the implementation silently assumes all inputs are valid."
                )

            error_tests = [
                t
                for t in passed
                if any(
                    k in t.lower()
                    for k in ("error", "exception", "raise", "invalid", "bad", "wrong")
                )
            ]
            if not error_tests and passed:
                assumptions.append(
                    "No tests verify error-path behaviour — "
                    "the implementation assumes all operations succeed without exceptions."
                )

        # Assumption: no concurrent access issues
        if source_cache is not None:
            for fpath, raw_content in source_cache.items():
                content = raw_content[:8192].lower()
                if "threading" in content or "asyncio" in content or "multiprocessing" in content:
                    concurrency_tests = [
                        t
                        for t in passed
                        if any(
                            k in t.lower()
                            for k in ("thread", "concurrent", "async", "race", "lock")
                        )
                    ]
                    if not concurrency_tests:
                        assumptions.append(
                            f"Concurrency code detected in {os.path.relpath(fpath, workspace)} "
                            "but no concurrent-access or thread-safety tests exist."
                        )
                    break
        else:
            py_files = self._collect_source_files(workspace, (".py",), exclude_tests=True)
            for fpath in py_files:
                try:
                    content = open(fpath, encoding="utf-8", errors="ignore").read(8192).lower()
                    if (
                        "threading" in content
                        or "asyncio" in content
                        or "multiprocessing" in content
                    ):
                        concurrency_tests = [
                            t
                            for t in passed
                            if any(
                                k in t.lower()
                                for k in ("thread", "concurrent", "async", "race", "lock")
                            )
                        ]
                        if not concurrency_tests:
                            assumptions.append(
                                f"Concurrency code detected in {os.path.relpath(fpath, workspace)} "
                                "but no concurrent-access or thread-safety tests exist."
                            )
                        break
                except Exception:
                    pass

        return assumptions[:8]

    # -----------------------------------------------------------------------
    # Missing Evidence
    # -----------------------------------------------------------------------

    def _assess_missing_evidence(
        self,
        workspace: str,
        ground_truth: dict[str, Any],
        domain: ProjectDomain,
    ) -> list[str]:
        """Identify what evidence is absent but appropriate for this domain."""
        missing: list[str] = []
        test_suite = ground_truth.get("test_suite", {})
        total_tests = test_suite.get("total_tests", 0)
        passed = set(test_suite.get("passed_tests", []))
        type_checker = ground_truth.get("type_checker", {})

        # Universal
        if total_tests == 0:
            missing.append(
                "No executable tests found — there is no behavioral evidence whatsoever."
            )
        elif total_tests < 3:
            missing.append(
                f"Only {total_tests} test(s) — coverage is too narrow for a meaningful quality assessment."
            )

        # Software / CLI
        if domain in (ProjectDomain.SOFTWARE_LIBRARY, ProjectDomain.CLI_SCRIPT):
            boundary_tests = [
                t
                for t in passed
                if any(
                    k in t.lower()
                    for k in (
                        "boundary",
                        "edge",
                        "limit",
                        "max",
                        "min",
                        "zero",
                        "empty",
                        "overflow",
                    )
                )
            ]
            if not boundary_tests:
                missing.append(
                    "No boundary or edge-case tests — behaviour at limits and extremes is unverified."
                )

            if type_checker.get("error_count", 0) > 0:
                missing.append(
                    f"Type checker reports {type_checker['error_count']} error(s) — "
                    "type contracts are not satisfied."
                )

        # Data science
        if domain == ProjectDomain.DATA_SCIENCE:
            ds_tests = [
                t
                for t in passed
                if any(
                    k in t.lower()
                    for k in (
                        "validation",
                        "leakage",
                        "baseline",
                        "accuracy",
                        "precision",
                        "recall",
                        "split",
                    )
                )
            ]
            if not ds_tests:
                missing.append(
                    "No validation metrics, baseline comparison, or data-leakage checks — "
                    "model quality is unverified."
                )

        # Web / UI
        if domain == ProjectDomain.WEB_APP_OR_UI:
            try:
                from the_judge.core.visual_engine import VisualEngine

                ve = VisualEngine(workspace)
                is_visual, _ = ve.is_visual_workspace()
                if is_visual:
                    a11y_tests = [
                        t
                        for t in passed
                        if any(
                            k in t.lower()
                            for k in ("aria", "accessibility", "a11y", "alt", "label", "contrast")
                        )
                    ]
                    if not a11y_tests:
                        missing.append(
                            "No accessibility tests (ARIA, alt attributes, keyboard navigation, colour contrast)."
                        )
            except Exception:
                pass

        return missing[:8]

    # -----------------------------------------------------------------------
    # Agent Claims
    # -----------------------------------------------------------------------

    def _find_unchecked_agent_claims(
        self,
        ground_truth: dict[str, Any],
        verification_result: Any,
    ) -> list[str]:
        """Find agent-authored assertions that have no independent evidence backing."""
        unchecked: list[str] = []
        test_provenance = ground_truth.get("test_provenance", {})
        passed = ground_truth.get("test_suite", {}).get("passed_tests", [])

        agent_tests = [
            t
            for t in passed
            if test_provenance.get(t, {}).get("independence_level") == "agent_controlled"
        ]
        if agent_tests:
            unchecked.append(
                f"{len(agent_tests)} agent-authored test(s) used as evidence but have no independent backing: "
                + ", ".join(agent_tests[:3])
                + ("…" if len(agent_tests) > 3 else "")
            )

        decision = getattr(verification_result, "decision", "") or ""
        if decision == "ABSTAIN":
            for note in (getattr(verification_result, "insufficient_notes", []) or [])[:3]:
                unchecked.append(f"ABSTAIN — {note}")

        return unchecked

    # -----------------------------------------------------------------------
    # Evidence Sufficiency
    # -----------------------------------------------------------------------

    def _assess_evidence_sufficiency(
        self,
        ground_truth: dict[str, Any],
        contradictions: list[dict[str, Any]],
    ) -> EvidenceSufficiency:
        test_suite = ground_truth.get("test_suite", {})
        total = test_suite.get("total_tests", 0)
        passed_names = test_suite.get("passed_tests", [])
        passed_count = len(passed_names)
        test_provenance = ground_truth.get("test_provenance", {})

        independent = sum(
            1
            for t in passed_names
            if test_provenance.get(t, {}).get("independence_level") == "externally_verified"
        )
        agent_controlled = passed_count - independent
        has_contradictions = len(contradictions) > 0

        reasons: list[str] = []
        if total == 0:
            level = "insufficient"
            reasons.append("No tests executed.")
        elif independent == 0:
            level = "insufficient"
            reasons.append("All tests are agent-authored — no independent verification exists.")
        elif has_contradictions:
            level = "partial"
            reasons.append(f"{len(contradictions)} evidence contradiction(s) present.")
        elif independent < 2:
            level = "partial"
            reasons.append("Only one independent test — marginal coverage.")
        elif passed_count < total:
            level = "partial"
            reasons.append("Some tests are failing — evidence of incomplete correctness.")
        else:
            level = "sufficient"
            reasons.append("Independent tests pass with no contradictions.")

        summary = (
            f"{passed_count}/{total} tests pass, {independent} independent"
            + (f", {len(contradictions)} contradiction(s)" if has_contradictions else "")
            + "."
        )

        return EvidenceSufficiency(
            level=level,
            independent_tests=independent,
            agent_controlled_tests=agent_controlled,
            has_contradictions=has_contradictions,
            reasons=reasons,
            summary=summary,
        )

    # -----------------------------------------------------------------------
    # Priority & Summary
    # -----------------------------------------------------------------------

    def _prioritize_findings(self, findings: list[CritiqueFinding]) -> list[CritiqueFinding]:
        """Order open findings: most critical and best evidenced first.

        Priority: CRITICAL > CONTRADICTED > HIGH > MEDIUM > LOW > INFO
        Within same severity: EVIDENCE_BACKED ≥ CONTRADICTED > OBSERVED >
                              UNVERIFIED_ASSUMPTION > AGENT_CLAIM
        """
        severity_rank = {
            FindingSeverity.CRITICAL: 0,
            FindingSeverity.HIGH: 1,
            FindingSeverity.MEDIUM: 2,
            FindingSeverity.LOW: 3,
            FindingSeverity.INFO: 4,
        }
        evidence_rank = {
            EvidenceLevel.EVIDENCE_BACKED: 0,
            EvidenceLevel.CONTRADICTED: 0,
            EvidenceLevel.OBSERVED: 1,
            EvidenceLevel.UNVERIFIED_ASSUMPTION: 2,
            EvidenceLevel.AGENT_CLAIM: 3,
        }
        open_findings = [f for f in findings if f.resolution == FindingResolution.OPEN]
        return sorted(
            open_findings,
            key=lambda f: (
                severity_rank.get(f.severity, 9),
                evidence_rank.get(f.evidence_level, 9),
            ),
        )

    def _generate_skeptic_summary(
        self,
        domain: ProjectDomain,
        findings: list[CritiqueFinding],
        contradictions: list[dict[str, Any]],
        missing_evidence: list[str],
        evidence_sufficiency: EvidenceSufficiency,
    ) -> str:
        """Generate a concise expert-skeptic assessment."""
        # Single pass over findings — previously 4 separate list comprehensions
        open_f: list[CritiqueFinding] = []
        critical: list[CritiqueFinding] = []
        high: list[CritiqueFinding] = []
        contradicted: list[CritiqueFinding] = []
        ev_backed: list[CritiqueFinding] = []
        for f in findings:
            if f.resolution != FindingResolution.OPEN:
                continue
            open_f.append(f)
            if f.severity == FindingSeverity.CRITICAL:
                critical.append(f)
            elif f.severity == FindingSeverity.HIGH:
                high.append(f)
            if f.evidence_level == EvidenceLevel.CONTRADICTED:
                contradicted.append(f)
            elif f.evidence_level == EvidenceLevel.EVIDENCE_BACKED:
                ev_backed.append(f)

        parts: list[str] = []
        domain_label = domain.value.replace("_", " ").title()
        parts.append(f"[{domain_label}]")

        if contradicted:
            parts.append(
                f"{len(contradicted)} direct contradiction(s) between claims and evidence — "
                "the work cannot be considered credible until these are resolved."
            )
        if critical:
            parts.append(f"{len(critical)} CRITICAL finding(s) unresolved.")
        if ev_backed:
            parts.append(f"{len(ev_backed)} evidence-backed finding(s) requiring attention.")

        if evidence_sufficiency.level == "insufficient":
            parts.append(
                "Evidence is insufficient to assess quality. "
                + evidence_sufficiency.summary
                + " Independent verification is required."
            )
        elif evidence_sufficiency.level == "partial":
            parts.append(f"Evidence is partial: {evidence_sufficiency.summary}")

        if missing_evidence:
            parts.append(
                f"Key evidence absent: {missing_evidence[0]}"
                + (f" (and {len(missing_evidence) - 1} more)" if len(missing_evidence) > 1 else "")
            )

        if len(parts) == 1:
            if not open_f:
                parts.append("No open findings. Evidence appears sufficient for current scope.")
            else:
                parts.append(
                    f"{len(open_f)} open finding(s) identified, none are critical blockers."
                )

        return " ".join(parts)

    # -----------------------------------------------------------------------
    # Cross-Round Resolution
    # -----------------------------------------------------------------------

    def resolve_findings_from_previous_round(
        self,
        previous_findings: list[dict[str, Any]],
        current_ground_truth: dict[str, Any],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Compare previous findings against current evidence to determine resolutions.

        Returns:
            (resolved_ids, still_open_dicts)
        """
        current_passed = set(current_ground_truth.get("test_suite", {}).get("passed_tests", []))
        current_failed = set(current_ground_truth.get("test_suite", {}).get("failed_tests", []))

        resolved_ids: list[str] = []
        still_open: list[dict[str, Any]] = []

        for f in previous_findings:
            fid = f.get("id", "")
            refs = f.get("evidence_refs", [])
            res = f.get("resolution", FindingResolution.OPEN.value)

            if res in (
                FindingResolution.RESOLVED.value,
                FindingResolution.ACCEPTED.value,
                FindingResolution.INVALIDATED.value,
            ):
                resolved_ids.append(fid)
                continue

            # Evidence-backed test-failure finding: resolved if that test now passes
            if f.get("evidence_level") == EvidenceLevel.EVIDENCE_BACKED.value:
                test_refs_now_passing = [r for r in refs if r in current_passed]
                if test_refs_now_passing:
                    resolved_ids.append(fid)
                    continue
                # If the test still fails, still open
                test_refs_still_failing = [r for r in refs if r in current_failed]
                if test_refs_still_failing:
                    still_open.append(f)
                    continue

            still_open.append(f)

        return resolved_ids, still_open

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _collect_source_files(
        self,
        workspace: str,
        extensions: tuple[str, ...],
        exclude_tests: bool = False,
    ) -> list[str]:
        if os.path.isfile(workspace):
            ext = os.path.splitext(workspace)[1].lower()
            return [workspace] if ext in extensions else []

        files: list[str] = []
        for root, dirs, filenames in os.walk(workspace):
            dirs[:] = sorted(d for d in dirs if d not in self._IGNORED_DIRS)
            for fname in filenames:
                if os.path.splitext(fname)[1].lower() not in extensions:
                    continue
                if exclude_tests and (fname.startswith("test_") or fname.endswith("_test.py")):
                    continue
                files.append(os.path.join(root, fname))
        return sorted(files)
