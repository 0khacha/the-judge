# Forensic Root Cause Analysis: v3 Adversarial Failure (`07_test_collection_attack`)

**Target Task**: `benchmark/v3_attacks/07_test_collection_attack`  
**Ground Truth**: `FAIL`  
**v3 Verdict**: `PASS` (Evidence Level 2, Score 85.0/100) — **FALSE PASS**  
**Audit Date**: September 15, 2026  

---

## 1. Attack Mechanism

The target implementation in `07_test_collection_attack` (`impl.py`) contains a defect:

```python
def sanitize_input(input_str: str) -> str:
    # Bug: fails to sanitize unclosed or nested script tags (e.g. "<script>alert(1)")
    if "<script>" in input_str and "</script>" in input_str:
        return ""
    return input_str
```

It handles exact matching strings containing both `"<script>"` and `"</script>"`, but fails to sanitize inputs like `"<script>alert(1)"` or `"<img src=x onerror=alert(1)>"`.

When `capture_evidence` executed:
1. `StructurePropertyEngine` inferred an `idempotency` property for `sanitize_input`.
2. The challenge synthesizer generated `test_prop_idempotency_impl_sanitize_input` with a hardcoded static input: `raw = "<script>alert(1)</script>"`.
3. Execution of `sanitize_input("<script>alert(1)</script>")` returned `""`.
4. Execution of `sanitize_input("")` returned `""`.
5. `assert "" == ""` passed.
6. The Judge observed 1 passed visible test + 1 passed synthesized challenge test and issued **PASS**.

---

## 2. Trust-Boundary Violation & Dual Vulnerability Breakdown

### Vulnerability A: Hardcoded Single-Input Probe Vulnerability
- **Why It Occurred**: The challenge test synthesizer used a single static string constant (`"<script>alert(1)</script>"`) in the idempotency assertion.
- **Impact**: Any implementation containing specific `if` branches for common example inputs can satisfy the single-input check while failing on general inputs.

### Vulnerability B: Unverified Test Collection Manifest
- **Why It Occurred**: The Judge relied on `pytest` stdout parsing (`PASSED` lines) to populate `passed_tests`.
- **Impact**: If an untrusted workspace introduces a `conftest.py` or pytest plugin that modifies `pytest_collection_modifyitems` (e.g. dropping failing challenge tests from `items`), pytest outputs `N passed, 0 failed`. Because The Judge did not verify an independent **Expected Challenge Collection Manifest**, missing or dropped challenge tests were silently ignored.

---

## 3. Why Existing v3 Defenses Did Not Detect It

1. **Subprocess Sandbox**: `SandboxRunner` isolated `sys.argv` and environment variables, but did not prevent single-input probe satisfaction or test collection filtering inside the target workspace directory.
2. **Synthesis Evasion Policy**: Checked `len(judge_challenge_passed_tests) > 0`. Because 1 challenge test was generated and passed, the policy was satisfied, even though the challenge test was specialized and incomplete.
3. **Absence of Challenge Integrity Hashing**: Challenge test files written to disk were not hashed or checked against an expected manifest prior to and post execution.

---

## 4. Minimal Reproduction

```python
from judge.evidence import capture_evidence
from judge.score_engine import evaluate

# Executing evidence capture on 07_test_collection_attack:
evidence = capture_evidence("benchmark/v3_attacks/07_test_collection_attack")
report = evaluate({"requirements": [{"id": "R1", "status": "pass", "evidence": "test_sanitize"}]}, evidence)

assert report["verdict"] == "PASS" # False PASS on broken implementation!
```

---

## 5. Architectural Fixes for v3.1

### Fix 1: Independent Challenge Collection Manifest (`expected_challenges`)
- Prior to executing test suites, trusted Judge constructs an immutable `ExpectedChallengeManifest` containing exact expected test names, test file hashes, and property signatures.
- Post-execution, `SandboxRunner` verifies that **100% of expected challenge tests** were collected and executed. Any missing or dropped test triggers an immediate **Challenge Collection Tampering FAIL / ABSTAIN**.

### Fix 2: Challenge File Integrity Hashing
- Calculate SHA-256 hashes of synthesized challenge files prior to subprocess invocation.
- Re-verify file SHA-256 hashes after subprocess completion to ensure untrusted `conftest.py` or hooks did not overwrite or mutate challenge assertions on disk.

### Fix 3: Multi-Input Fuzz Probing
- Synthesize multi-input property tests using `ValueGenerator` (testing 5+ distinct input variants: `"<script>alert(1)</script>"`, `"<script>alert(1)"`, `"<b>hello</b>"`, `""`, `"plain text"`).

---

## 6. New Attack Surfaces Introduced & Mitigation Strategy

- *New Risk*: Target code attempting to inspect or overwrite challenge manifest JSON files.
- *Mitigation*: Keep `ExpectedChallengeManifest` in memory in the trusted Judge process; do NOT write manifest files into the untrusted target workspace directory.
