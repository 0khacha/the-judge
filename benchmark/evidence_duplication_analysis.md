# Evidence Duplication Analysis

**Scope**: Investigation of Repeated Context and Subprocess Executions in The Judge Repair Loop  
**Tasks Analyzed**: `01_auth_jwt`, `09_password_hasher`, `11_luhn_validator`  
**Date**: 2026-09-21  

---

## Executive Summary

In Condition C (The Judge + Repair Loop), several tasks hit the maximum round limit (`max_rounds=5`) while processing completely unchanged files and producing identical test outputs.

Across all 12 tasks in the benchmark:
- **Total trials analyzed**: 12 tasks in Condition C
- **Trials experiencing high duplication**: 3 tasks (`01_auth_jwt`, `09_password_hasher`, `11_luhn_validator`)
- **Duplication ratio in those tasks**: **63.0% to 66.8%** of all bytes processed were pure repetitions
- **Total repeated bytes in those 3 tasks alone**: **30,341 bytes** (out of 32,460 bytes across the entire suite)

This analysis measures the exact mechanics of this duplication, explains why the current system fails to detect it, and defines structural solutions for both the benchmark and The Judge engine.

---

## 1. Empirical Measurements Per Task

### Task 1: `01_auth_jwt`
- **Total Rounds**: 5
- **Starting Code**: Expiration check missing in `decode_token()`.
- **Round-by-Round Breakdown**:

| Round | Workspace File Hash (`jwt_auth.py`) | Judge Score | Decision | Blocking Issues Count | Findings Count | Oracle Fix Effect |
|---|---|---|---|---|---|---|
| 1 | `22ba0ae5c74e` | 61.92 | FAIL | 10 | 18 | Fixed `jwt_auth.py` |
| 2 | `d5cee56d70ac` | 61.92 | FAIL | 10 | 18 | Rewrote identical content |
| 3 | `d5cee56d70ac` (identical) | 61.92 | FAIL | 10 | 18 | Rewrote identical content |
| 4 | `d5cee56d70ac` (identical) | 61.92 | FAIL | 10 | 18 | Rewrote identical content |
| 5 | `d5cee56d70ac` (identical) | 61.92 | FAIL | 10 | 18 | Max rounds exhausted |

- **Repetition Summary**:
  - File snapshots: Rounds 2, 3, 4, 5 had **100% identical SHA-256 hashes** (`d5cee56d70ac`).
  - Findings: The exact same 10 blocking issues and 18 findings were emitted in all 5 rounds.
  - Subprocess calls: 5 sandbox pytest runs + 5 visible pytest runs = 10 subprocess executions. Rounds 2–5 (8 executions) were redundant.
  - Duplication ratio: **63.02%** (16,270 repeated bytes).

---

### Task 2: `09_password_hasher`
- **Total Rounds**: 5
- **Starting Code**: Hardcoded static salt `salt = "static_salt_123"`.
- **Round-by-Round Breakdown**:

| Round | Workspace File Hash (`password_hasher.py`) | Judge Score | Decision | Blocking Issues Count | Findings Count | Oracle Fix Effect |
|---|---|---|---|---|---|---|
| 1 | `e1cbb4b63bf8` | 67.00 | FAIL | 4 | 6 | Fixed `password_hasher.py` |
| 2 | `02955853d1cb` | 78.00 | FAIL | 3 | 4 | Rewrote identical content |
| 3 | `02955853d1cb` (identical) | 78.00 | FAIL | 3 | 4 | Rewrote identical content |
| 4 | `02955853d1cb` (identical) | 78.00 | FAIL | 3 | 4 | Rewrote identical content |
| 5 | `02955853d1cb` (identical) | 78.00 | FAIL | 3 | 4 | Max rounds exhausted |

- **Repetition Summary**:
  - In Round 1, `apply_fix.py` updated the password hasher to use random salts. The Judge score increased from 67.0 to 78.0.
  - However, 3 synthesized property tests continued to fail (`test_prop_boundary_perturbation_password_hasher_...`).
  - Rounds 2, 3, 4, and 5 operated on **100% identical file content** (`02955853d1cb`).
  - Findings and blocking issues in Rounds 2–5 were identical.
  - Duplication ratio: **66.18%** (7,392 repeated bytes).

---

### Task 3: `11_luhn_validator`
- **Total Rounds**: 5
- **Starting Code**: Off-by-one boundary `doubled > 10` instead of `> 9`.
- **Round-by-Round Breakdown**:

| Round | Workspace File Hash (`luhn.py`) | Judge Score | Decision | Blocking Issues Count | Findings Count | Oracle Fix Effect |
|---|---|---|---|---|---|---|
| 1 | `42272de22b09` | 63.33 | FAIL | 3 | 4 | Fixed `luhn.py` |
| 2 | `9edd56755de7` | 63.33 | FAIL | 3 | 4 | Rewrote identical content |
| 3 | `9edd56755de7` (identical) | 63.33 | FAIL | 3 | 4 | Rewrote identical content |
| 4 | `9edd56755de7` (identical) | 63.33 | FAIL | 3 | 4 | Rewrote identical content |
| 5 | `9edd56755de7` (identical) | 63.33 | FAIL | 3 | 4 | Max rounds exhausted |

- **Repetition Summary**:
  - In Round 1, `apply_fix.py` fixed `doubled > 9`.
  - In Rounds 2–5, synthesized boundary tests continued to fail due to type mismatch (`TypeError: 'float' object is not iterable` from `fn(1.0)` / `fn(10.0)`).
  - Rounds 2 through 5 were executed on **100% identical file content** (`9edd56755de7`).
  - Duplication ratio: **66.79%** (6,679 repeated bytes).

---

## 2. Root Cause Analysis: Why Duplication Occurs

### Cause 1: Static Oracle Loop Ignorance
In Condition C, the "agent" is a static Python script (`apply_fix.py`).
- It does not read The Judge's `findings` or `suggested_focus`.
- It performs a one-shot deterministic replacement of the target file.
- When The Judge fails on Round 2 (because of challenge tests that the fix did not resolve), the repair loop calls `apply_fix.py` again.
- Because `apply_fix.py` is idempotent, it writes the exact same bytes to disk.
- The loop continues executing blindly until `max_rounds=5`.

### Cause 2: Missing Stagnation and Idempotency Guard in the Loop
A well-designed repair loop must monitor:
1. **Workspace Hash Delta**: If `sha256(workspace)` before repair == `sha256(workspace)` after repair, no change occurred. Running verification again is guaranteed to yield the same result.
2. **Score & Findings Stagnation**: If Round $N$ and Round $N-1$ have identical `(numeric_score, blocking_issues)`, the repair attempt failed to change the evaluation outcome.
3. **Oracle Script Saturation**: Once a static script has run once, running it again without code changes cannot produce new behavior.

### Cause 3: Benchmark Re-running Visible Tests Every Round
In `conditions.py`:
- `verify()` runs pytest inside a sandbox.
- The benchmark runner then ran `_run_pytest_visible()` separately in the same round for comparison.
- In `11_luhn_validator`, this ran 5 visible pytest executions that produced identical `1 passed in 0.01s` output, adding ~2,800 bytes of pure stdout duplication per task.

---

## 3. Engineering Costs of Duplication

1. **Subprocess Invocations**:
   - For the 3 stuck tasks, 24 out of 33 subprocess calls were 100% redundant.
   - At ~1.0s to ~2.5s per subprocess, this added ~40 seconds of wasted wall-clock time in a single 36-trial benchmark run.
2. **Token-Equivalent Context Waste**:
   - Over **30.3 kB** of identical source files and test logs were repeatedly loaded and analyzed across these three tasks.
   - In an LLM-driven agent setup, feeding identical context and identical failure logs across 4 rounds would consume thousands of un-cached or cached tokens without progress.

---

## 4. Required Fixes and Safeguards

### In the Benchmark / Repair Loop (`conditions.py` & `repair_loop.py`):
1. **Workspace Hash Check Before and After Repair**:
   Before running repair, record `hash_before = hash_workspace(dir)`.
   After repair, compute `hash_after = hash_workspace(dir)`.
   If `hash_before == hash_after`:
   `BREAK` immediately with reason: `"Repair produced no workspace modifications; stopping loop."`
2. **Score Stagnation Detection**:
   Maintain a history of `(round_score, set(blocking_issues))`.
   If current state matches previous state after an attempted repair, terminate early with reason: `"Verification state stagnated; no score progression."`
3. **Separate Benchmark Instrumentation**:
   Do not execute visible pytest inside the loop for Condition C; rely on `verify()`'s internal test execution.

---

## 5. Conclusion

Context duplication in this benchmark is not a random statistical anomaly; it is a deterministic failure mode when an automated verification loop encounters an intractable finding. Introducing workspace hash delta checking and stagnation guards will immediately eliminate 63–67% of wasted overhead in these tasks without compromising verification accuracy.
