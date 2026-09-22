# Benchmark Audit Report

**Scope**: `benchmark/benchmark_abc/` implementation  
**Date**: 2026-09-21  
**Benchmark run**: `raw/run_20260921T181337.jsonl` (36 trials, seed=42)

---

## Summary

The benchmark infrastructure is structurally sound — isolation, hidden-test independence,
and JSON output are implemented correctly. Several metric definitions are misleading or
mathematically inconsistent, and three specific implementation flaws produce incorrect
findings in the report. One confirmed regression (Luhn) is correctly classified in the
per-task JSON but incorrectly dismissed in the report narrative.

---

## 1. CRITICAL Issues

### C-1: Report Section K falsely states "No regression cases observed"

**File**: `report_generator.py`, Section K Q5  
**Evidence**: `per_task.json` line 234 — `judge_contribution: "REGRESSION"` for `11_luhn_validator`  
**Observed**: `benchmark_report.md` Section K reads:
> "No regression cases observed: The Judge did not produce FALSE_FAIL on any task
> that Baseline/Generic Review got right."

**Actual data**:
- Baseline: `11_luhn_validator` → TRUE_PASS (code is correct, hidden test passes)
- Generic Review: `11_luhn_validator` → TRUE_PASS
- The Judge: `11_luhn_validator` → FALSE_FAIL (Judge incorrectly says FAIL on correct code)

This is the definition of a regression. The statement is factually wrong.  
**Impact**: Causes the report to misrepresent The Judge's reliability.  
**Fix**: Section K must state "1 regression confirmed: 11_luhn_validator."

---

### C-2: Misleading "Quality delta = -50.0%" headline conceals the success_rate denominator asymmetry

**File**: `report_generator.py`, Section C quality-vs-cost table  
**Problem**: `success_rate = TP / total_gt_pass`. This denominator **differs per condition**:
- Baseline: `total_gt_pass = 1` (only luhn_validator passes hidden tests on broken code)
- The Judge: `total_gt_pass = 6` (oracle fixes 3 additional workspaces, making them correct)

Comparing `100%` (Baseline, 1/1) with `50%` (Judge, 3/6) **across different denominators**
is not a valid comparison. The report displays this as "quality delta = -50.0%" without
disclosing the denominator difference.

**Correct framing**: Use "Final Correct Implementation Rate" = (TP + FN) / 12 tasks:
- Baseline: 1/12 = 8.3%
- Generic Review: 1/12 = 8.3%
- The Judge: 6/12 = 50.0% (code is actually correct in 6 workspaces; Judge correctly
  reports PASS on 3 of them and incorrectly says FAIL on the other 3)

**Impact**: The headline metric is mathematically misleading and suggests The Judge
performs worse on quality, when the opposite is true for end-to-end outcome.  
**Fix**: Add "Final Correct Implementation Rate" and label `success_rate` carefully.

---

### C-3: The benchmark applies `apply_fix.py` in Condition C at every FAIL round, regardless of oracle existence

**File**: `conditions.py`, `run_condition_c_the_judge()`  
**Problem**: When `apply_fix.py` exists but the oracle fix does NOT resolve the challenge
tests (e.g., Luhn, password_hasher, auth_jwt), the loop applies the same fix up to 5
times, creating 4 redundant rounds. Each round:
- Re-runs the full sandbox
- Produces identical blocking issues
- Applies the same oracle fix again (overwriting the same file)
- Generates the same test output

This inflates subprocess counts, byte metrics, and duplication ratios for exactly those
tasks where The Judge is struggling most.

**Evidence** (from round histories):
- `11_luhn_validator`: 5 rounds, same blocking issues in rounds 2–5, fix applied 5 times
- `09_password_hasher`: 5 rounds, identical blocking in rounds 2–5
- `01_auth_jwt`: 5 rounds, same 10 blocking issues per round

**Existing early-stopping logic in `conditions.py` lines 119-126** checks for unchanged
test pass/fail sets but is bypassed here because the test NAMES change between rounds
(challenge synthesis generates different random test IDs each round).

**Impact**: The benchmark's duplication analysis (19.7% mean, 63-67% for three tasks)
**understates** the true redundancy because the file bytes change (fix rewrites file) but
the blocking causes are identical.

**Fix**: Track blocking issues hash per round. If blocking issues are identical across two
consecutive rounds and no file content changed, stop. (Or: if apply_fix.py has already been
applied once with no score improvement, stop — the oracle is not sufficient.)

---

## 2. HIGH Issues

### H-1: `success_rate` vs `recall` — identical values with different names

**File**: `analysis.py`, `compute_condition_summary()`  
**Problem**: `success_rate = TP / total_gt_pass` and `recall = TP / total_gt_pass` are
computed identically but named differently. They produce the same number.  
**Impact**: Table duplication causes confusion.  
**Fix**: Remove one. Keep `recall` (standard terminology) and remove `success_rate`, or
replace `success_rate` with the "Final Correct Implementation Rate" (TP+FN)/n.

---

### H-2: "Cost per success" metric has undefined meaning when denominators differ

**File**: `report_generator.py`, Section C quality-vs-cost table  
**Problem**: "Cost per success" = total_tokens / TP. When TP=1 for Baseline and TP=3 for
The Judge, the metric compares incommensurable quantities and appears to show The Judge
is cheaper per success (6484 vs 5902), obscuring the 3.3× total overhead.  
**Impact**: Misleads cost analysis.  
**Fix**: Either remove it or restate as "total token-equivalents per TRUE_PASS outcome"
with a clear note that baseline has 1 TP vs judge's 3 TP.

---

### H-3: Separate "detection performance" from "repair performance" from "end-to-end correctness"

**File**: `report_generator.py` generally  
**Problem**: The report conflates three distinct measurements:

1. **Detection**: Does The Judge correctly identify that the starting code is broken?
   (FALSE_PASS rate on GT=FAIL tasks — measured on initial code before any fix)
2. **Repair success**: After The Judge triggers the oracle fix, does the final code pass?
   (TRUE_PASS on tasks where apply_fix.py existed)
3. **End-to-end correctness**: Does the pipeline (Judge + repair) produce correct final code?
   (TP + FN) / 12

These are currently mixed in the outcome matrix, making it impossible to answer each
question independently.

---

### H-4: "Agreement" classification for auth_jwt and password_hasher is wrong

**File**: `analysis.py`, `compute_per_task_comparison()`  
**Problem**: `01_auth_jwt` is classified as "AGREEMENT" because the contribution logic
only checks exact outcome equality. But:
- Baseline: FALSE_PASS (claims PASS on broken code)
- Generic Review: FALSE_PASS (claims PASS on broken code)
- The Judge: FALSE_FAIL (claims FAIL on **fixed** code that actually now passes)

These are different failure modes, not agreement. The Judge DETECTED the problem
(triggered apply_fix.py) — that is a different outcome than "no review."

Similarly for `09_password_hasher`.

**Fix**: Separate "AGREE_ALL_WRONG" from "DETECT_BUT_CANT_VERIFY".

---

### H-5: Benchmark adds a visible-test subprocess inside Condition C per round

**File**: `conditions.py`, `run_condition_c_the_judge()`, approx. line 145-155  
**Problem**: Each round in Condition C calls `_run_pytest_visible()` AFTER `verify()`.
This is benchmark instrumentation — the real Judge does not do this. It inflates:
- `subprocess_calls_MEASURED` (adds 1 per round beyond the verify() call)
- `output_bytes_ESTIMATED`
- `duplication ratios` (because the same visible test output is repeated)

**Impact**: The mean subprocess count of 5.5 for The Judge includes this instrumentation
overhead, making it look more expensive than it is in production.  
**Fix**: Move visible-test metrics to a separate measurement pass, or label them
"benchmark_instrumentation_calls_MEASURED" and exclude from the production-cost summary.

---

## 3. MEDIUM Issues

### M-1: "token-equivalent estimates" called "tokens" in some table headers

**File**: `report_generator.py`  
**Problem**: Several table rows say "Mean total token-equiv" and "Token-Equivalent Usage"
which is correct in the table but the section header "Token / Cost Results" implies real
LLM tokens. The note is present but easy to miss.  
**Fix**: Add "(NO LLM — byte proxies only)" to the section header.

---

### M-2: Duplication analysis counts rounds with no change to apply_fix.py

**File**: `instrumentation.py`, `detect_context_duplication()`  
**Problem**: For tasks where apply_fix.py runs but the oracle fix does not resolve
the challenge tests, the file content changes on round 1 (fix applied) but then is
identical for rounds 2–5 (same fix re-applied). The current logic counts
`repeated_file_content_rounds` correctly, but the label "3 rounds sent unchanged file
content" is misleading — the file was re-written each round but to identical content.

---

### M-3: task_catalog.py asserts luhn_validator has a defect

**File**: `task_catalog.py`, line for `11_luhn_validator`  
**Problem**: The catalog labels luhn_validator as `defect_type=logic` with a "Luhn
algorithm implementation flaw." But the **hidden test passes on the starting code**
(GT=PASS for Baseline). This means the hidden test does not exercise the `> 10` vs
`> 9` boundary. The starting code is "correct enough" to pass all tests that matter.

The catalog description is misleading — the starting code has a latent defect
(`> 10` misses exactly `doubled=10`), but the test suite (visible + hidden) does not
exercise a card number that triggers it.

**Root cause of the regression**: The challenge synthesis **does** generate boundary
perturbation tests for the exact `> 10` boundary. These tests **correctly detect** the
latent defect — but the oracle fix also fails them, indicating the fixed code itself
has a problem, OR the synthesized tests have incorrect expected values.

---

### M-4: False PASS rate computation: denominator uses PASS CLAIMS, not total tasks

**File**: `analysis.py`  
**Problem**: `false_pass_rate = FP / (TP + FP)` where the denominator is "all PASS
claims." For Baseline with 12 PASS claims: 11/12 = 91.7%. This is correct precision
from a classification perspective.

However, when comparing to The Judge with only 9 PASS claims, the denominators differ.
The Judge makes fewer claims (it says FAIL on 3 tasks), so its false_pass_rate is computed
over a smaller set. This is mathematically valid but should be disclosed: The Judge's
lower FPR partly reflects that it makes fewer PASS claims, not only that its claims are
more accurate.  
**Fix**: Add FP/total_tasks as a supplementary metric ("unconditional false PASS rate").

---

## 4. LOW Issues

### L-1: context_duplication.json includes 1-round trials

The per_trial_duplication list includes 7 tasks with 0% duplication (single-round trials).
This inflates the "12 trials analyzed" count and reduces the reported mean ratio. The mean
should be computed only over multi-round trials.

### L-2: The `judge_contribution: "AGREEMENT"` for 8 tasks includes different failure modes

Four tasks (api_rate_limiter, bounded_queue, inventory_refactor, tiered_discount) agree
because ALL conditions produce FALSE_PASS — the defect is invisible to all conditions.
Three tasks (auth_jwt, password_hasher, input_sanitizer) have more complex outcomes.
Grouping them all as "AGREEMENT" obscures whether The Judge adds or subtracts value.

### L-3: Regression rate = 0.0% is wrong

**File**: `analysis.py`, `compute_condition_summary()` for "the_judge"  
The metric "regression rate = trials with regressions / total" counts Judge-produced
regressions (previously-passing behavior re-broken by repair). The `regressions` field
in condition results tracks the score engine's regression detection, not the Luhn case.
The Luhn case is a **benchmark-level regression** (Judge verdict worse than baseline)
which should be separately tracked.

---

## 5. Things That Are Already Correct

- **Workspace isolation**: Each trial uses a fresh `tempfile.mkdtemp()` — no contamination
- **Hidden-test isolation**: Hidden tests run AFTER condition completes, on the final workspace state
- **MEASURED/ESTIMATED/UNAVAILABLE labeling**: Consistently applied throughout
- **per-task JSONL recording**: Complete, auditable, non-destructive
- **Luhn classification in per_task.json**: Correctly shows `judge_contribution: "REGRESSION"`
- **Advantage analysis JSON**: Correctly identifies 3 improvements and 1 regression
- **Trial ordering randomization**: Seed-controlled shuffle applied before execution
- **No hidden test leakage**: The hidden_tests directory is never used as input to conditions A/B/C

---

## 6. Recommended Fixes (Priority Order)

| # | Fix | Severity | Effort |
|---|-----|----------|--------|
| 1 | Remove false "No regression cases observed" from report | CRITICAL | Low |
| 2 | Replace success_rate with Final Correct Implementation Rate | CRITICAL | Low |
| 3 | Add DETECT_BUT_CANT_VERIFY category to per-task matrix | HIGH | Medium |
| 4 | Separate Detection / Repair / End-to-end sections in report | HIGH | Medium |
| 5 | Label instrumentation subprocess calls separately | HIGH | Low |
| 6 | Fix duplication mean to use only multi-round trials | MEDIUM | Low |
| 7 | Fix task_catalog.py luhn description | MEDIUM | Low |
| 8 | Add FP/total as supplementary false-pass metric | MEDIUM | Low |
| 9 | Stop repair loop when same blocking issues repeat across rounds | CRITICAL | Medium |

---

## 7. Luhn Regression Root Cause (Preview)

Full analysis in `benchmark/luhn_regression_analysis.md`.

**Short summary**: The Judge's challenge synthesis generates boundary-perturbation tests
(`test_prop_boundary_perturbation_luhn_validate_luhn_1`, `..._9`, `..._10`) that test
specific card numbers. These tests fail on the **original** code (expected — the `> 10`
vs `> 9` flaw is real). After apply_fix.py runs, the `> 9` boundary is correct. However,
**the same synthesized tests continue to fail on the fixed code**, suggesting the challenge
synthesizer is generating tests with **incorrect expected values** or testing inputs where
`doubled=10` is not present in the test data.

This is a **challenge synthesis defect**: the synthesizer generates tests that claim to
test the boundary but the assertions do not match the correct Luhn algorithm output.
The repair loop therefore cycles at 5 rounds, consuming 7.53× the baseline token-equivalent,
while degrading from TRUE_PASS (baseline) to FALSE_FAIL (Judge).

---

## 8. Evidence Duplication Root Cause (Preview)

Full analysis in Phase 5.

**Short summary**: For auth_jwt, password_hasher, and luhn_validator, apply_fix.py is
called at the end of every FAIL round. On round 2, the fix changes the file. On rounds
3–5, the fix re-writes the same content (the oracle is idempotent). The challenge
synthesis then re-generates from the same (now-fixed) source — but produces slightly
different test IDs each round, preventing the early-stopping check from halting.
The result is 3–4 rounds of effectively identical work at 63–67% content repetition.
