"""
task_catalog.py — Catalog of benchmark tasks with difficulty and defect metadata.

This module defines all 12 original benchmark tasks without modifying them.
Difficulty labels are assigned based on the type of defect and the likelihood
that visible-test-only review would catch it.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Task difficulty definitions
# ---------------------------------------------------------------------------
EASY = "easy"
MEDIUM = "medium"
HARD = "hard"

# ---------------------------------------------------------------------------
# Defect category definitions
# ---------------------------------------------------------------------------
DEFECT_SECURITY = "security"          # Vulnerability: auth bypass, weak crypto, etc.
DEFECT_LOGIC = "logic"                # Incorrect algorithm / boundary
DEFECT_STATE = "state"                # Stateful bug: race, eviction, reservation
DEFECT_MISSING_REQ = "missing_req"   # Requirement not implemented at all
DEFECT_RETRY = "retry"               # Incorrect retry / backoff behavior
DEFECT_TRANSACTION = "transaction"   # DB / transactional atomicity


# ---------------------------------------------------------------------------
# Defect nature definitions
# ---------------------------------------------------------------------------
DEFECT_NATURE_TESTED = "TESTED_DEFECT"   # Exercised by evaluator tests
DEFECT_NATURE_LATENT = "LATENT_DEFECT"   # Exists in code but not exercised by current test suite


# ---------------------------------------------------------------------------
# TaskInfo dataclass (plain dict for simplicity — no external deps)
# ---------------------------------------------------------------------------
def _task(
    task_id: str,
    name: str,
    difficulty: str,
    defect_type: str,
    defect_summary: str,
    visible_tests_catch_defect: bool,
    judge_hypothesis: str,
    defect_nature: str = DEFECT_NATURE_TESTED,
) -> Dict:
    """Build a task catalog entry."""
    return {
        "task_id": task_id,
        "name": name,
        "difficulty": difficulty,
        "defect_type": defect_type,
        "defect_summary": defect_summary,
        "defect_nature": defect_nature,
        # Whether the visible (non-hidden) tests already catch the defect.
        # If True, Generic Review (B) should catch it; Judge (C) should too.
        # If False, only The Judge or hidden tests can catch it.
        "visible_tests_catch_defect": visible_tests_catch_defect,
        # Expected hypothesis about what The Judge adds vs. baseline.
        "judge_hypothesis": judge_hypothesis,
    }


TASK_CATALOG: List[Dict] = [
    _task(
        task_id="01_auth_jwt",
        name="Auth JWT Verification",
        difficulty=MEDIUM,
        defect_type=DEFECT_SECURITY,
        defect_summary=(
            "Expiration check is commented out — expired tokens are accepted silently. "
            "The visible tests do not test expiration. Only hidden test does."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Baseline and Generic Review both fail (visible tests pass on broken code). "
            "The Judge may detect the missing expiry gate only if its challenge synthesizer "
            "generates a temporal property check — otherwise it too will fail."
        ),
    ),
    _task(
        task_id="02_api_rate_limiter",
        name="API Rate Limiter",
        difficulty=MEDIUM,
        defect_type=DEFECT_STATE,
        defect_summary=(
            "Rate limiting state is not per-user — all users share the same counter. "
            "Visible tests check only single-user behavior."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Baseline/Generic Review both PASS (visible tests pass). "
            "The Judge may catch the shared-state defect via behavioral property checks."
        ),
    ),
    _task(
        task_id="03_input_sanitizer",
        name="Input Sanitizer",
        difficulty=EASY,
        defect_type=DEFECT_LOGIC,
        defect_summary=(
            "Sanitization is incomplete — certain dangerous characters pass through. "
            "Visible tests may not exercise all edge cases."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Baseline fails (no review). Generic Review may fail if visible tests miss edges. "
            "Judge adds value if its challenge synthesizer generates perturbation inputs."
        ),
    ),
    _task(
        task_id="04_json_schema_parser",
        name="JSON Schema Parser",
        difficulty=MEDIUM,
        defect_type=DEFECT_LOGIC,
        defect_summary=(
            "Array item type validation is not implemented — strings inside integer arrays pass. "
            "Hidden test specifically checks this edge case."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Baseline/Generic Review PASS (visible tests don't test item types). "
            "The Judge may catch via array-item boundary check synthesis."
        ),
    ),
    _task(
        task_id="05_transaction_db",
        name="Transaction Database",
        difficulty=HARD,
        defect_type=DEFECT_TRANSACTION,
        defect_summary=(
            "Failed transactions are not rolled back — partial writes persist. "
            "Requires atomicity guarantee that the visible tests do not check."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "The Judge advantages were measured in existing benchmark — this task was in "
            "judge_advantage list. apply_fix.py + Judge verify = correct detection."
        ),
    ),
    _task(
        task_id="06_http_retry_client",
        name="HTTP Retry Client",
        difficulty=MEDIUM,
        defect_type=DEFECT_RETRY,
        defect_summary=(
            "Exponential backoff is not implemented correctly — retry delay is fixed or wrong."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Visible tests likely mock timing, so Generic Review passes incorrectly. "
            "Judge may or may not detect depending on challenge synthesis."
        ),
    ),
    _task(
        task_id="07_lru_cache_ttl",
        name="LRU Cache with TTL",
        difficulty=HARD,
        defect_type=DEFECT_STATE,
        defect_summary=(
            "TTL expiration logic is missing or incorrect — expired entries are returned. "
            "Visible tests test LRU eviction only (not TTL). Only hidden test checks TTL."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "This task was in judge_advantage in existing benchmark — Judge detects TTL flaw, "
            "Baseline/Generic Review do not."
        ),
    ),
    _task(
        task_id="08_bounded_queue",
        name="Bounded Queue",
        difficulty=EASY,
        defect_type=DEFECT_LOGIC,
        defect_summary=(
            "Capacity guard is missing — queue accepts items beyond max size."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Baseline/Generic Review both fail if visible tests don't test overflow. "
            "Judge may catch via property check on bounded behavior."
        ),
    ),
    _task(
        task_id="09_password_hasher",
        name="Password Hasher",
        difficulty=HARD,
        defect_type=DEFECT_SECURITY,
        defect_summary=(
            "Static salt used across all passwords — identical passwords produce identical hashes. "
            "This is a critical security vulnerability not caught by functional tests."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "This task was in judge_advantage in existing benchmark — Judge detects static salt "
            "security vulnerability. Baseline/Generic Review pass incorrectly."
        ),
    ),
    _task(
        task_id="10_inventory_refactor",
        name="Inventory Refactor",
        difficulty=MEDIUM,
        defect_type=DEFECT_STATE,
        defect_summary=(
            "Stock reservation does not prevent over-allocation — deficit is possible."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "This task was NOT in judge_advantage in existing benchmark (agreement=both fail). "
            "Neither B nor C catches this defect — apply_fix does not exist or doesn't fully fix."
        ),
    ),
    _task(
        task_id="11_luhn_validator",
        name="Luhn Validator",
        difficulty=EASY,
        defect_type=DEFECT_LOGIC,
        defect_summary=(
            "Starting code contains latent boundary flaw: 'if doubled > 10' misses doubled==10 "
            "(only triggered when digit 5 is at an odd index). However, the existing test suite "
            "(visible and hidden) does not exercise this specific case, so Baseline and Generic Review "
            "both achieve TRUE_PASS against the evaluation suite. The Judge synthesizes boundary tests "
            "that pass float literals to a str-typed parameter, causing a TypeError regression (FALSE_FAIL)."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "Starting code passes hidden tests despite latent flaw. The Judge synthesizes boundary tests "
            "but violates the string type contract, causing a confirmed regression to FALSE_FAIL."
        ),
        defect_nature=DEFECT_NATURE_LATENT,
    ),
    _task(
        task_id="12_tiered_discount",
        name="Tiered Discount Engine",
        difficulty=MEDIUM,
        defect_type=DEFECT_LOGIC,
        defect_summary=(
            "Discount tier boundary is off — wrong rate applied at tier thresholds."
        ),
        visible_tests_catch_defect=False,
        judge_hypothesis=(
            "This task was in judge_advantage in existing benchmark — Judge detects boundary flaw. "
            "apply_fix + verify loop = correct outcome."
        ),
    ),
]

# Build lookup map by task_id for quick access
TASK_BY_ID: Dict[str, Dict] = {t["task_id"]: t for t in TASK_CATALOG}

# Group by difficulty
EASY_TASKS: List[str] = [t["task_id"] for t in TASK_CATALOG if t["difficulty"] == EASY]
MEDIUM_TASKS: List[str] = [t["task_id"] for t in TASK_CATALOG if t["difficulty"] == MEDIUM]
HARD_TASKS: List[str] = [t["task_id"] for t in TASK_CATALOG if t["difficulty"] == HARD]

# Group by defect type
TASKS_BY_DEFECT: Dict[str, List[str]] = {}
for _t in TASK_CATALOG:
    TASKS_BY_DEFECT.setdefault(_t["defect_type"], []).append(_t["task_id"])

# Tasks expected to show Judge advantage (from prior benchmark run)
EXPECTED_JUDGE_ADVANTAGE: Tuple[str, ...] = (
    "05_transaction_db",
    "07_lru_cache_ttl",
    "09_password_hasher",
    "12_tiered_discount",
)

# Tasks where The Judge was NOT expected to help (both B and C fail, or both pass)
EXPECTED_AGREEMENT: Tuple[str, ...] = (
    "01_auth_jwt",
    "02_api_rate_limiter",
    "03_input_sanitizer",
    "04_json_schema_parser",
    "06_http_retry_client",
    "08_bounded_queue",
    "10_inventory_refactor",
    "11_luhn_validator",
)
