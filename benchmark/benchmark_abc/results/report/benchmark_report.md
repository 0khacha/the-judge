# Controlled Judge Detection & Repair-Loop Benchmark Report

_Generated: 2026-09-21T20:07:07Z_

---

> [!IMPORTANT]
> **Primary Objective & Methodological Scope**:
> This benchmark evaluates **The Judge** in a controlled, deterministic environment.
> The "coding agent" in Condition C is a deterministic oracle patch script (`apply_fix.py`),
> **NOT an LLM coding agent**. Furthermore, **The Judge itself does not invoke an LLM**;
> it is a deterministic Python subprocess verification engine.
> 
> Consequently, this benchmark measures **detection quality** (catching defects)
> and **verification-gated repair dynamics**, NOT proof that an LLM agent generates better code.
> All "token" metrics are labeled **token-equivalent estimates** (byte proxies: 4 bytes ≈ 1 token-equiv).

## A. Experimental Setup & Controls

- **Task Suite**: 12 distinct benchmark tasks from `benchmark/tasks/`
- **Conditions Evaluated**:
  - **Condition A (Baseline)**: Starting code submitted as-is; unconditionally claims PASS (0 review).
  - **Condition B (Generic Review)**: Runs visible unit test suite; claims PASS iff visible tests pass (no Judge hard gates or challenge synthesis).
  - **Condition C (The Judge)**: Runs `the_judge.api.verify()`. If FAIL, invokes `apply_fix.py` and re-verifies up to 5 rounds.
- **Randomization**: Shuffled execution order across tasks and conditions (Seed: `42`).
- **Workspace Isolation**: Every trial executes in a fresh `tempfile.mkdtemp()` directory; source task directories are never modified.
- **Independent Ground Truth**: Evaluated post-trial by running `hidden_tests/` via pytest in an isolated subprocess (never exposed to conditions A, B, or C).

## B. Detection Performance (Initial Code Evaluation)

Can The Judge correctly identify defective implementations on the initial starting code?

| Dimension | Baseline (A) | Generic Review (B) | The Judge (C) |
|---|---|---|---|
| Initial Defect Rejection Rate | 0.0% (0/12) | 0.0% (0/12) | 50.0% (6/12) |
| Initial Tasks Flagged as FAIL | 0 | 0 | 6 (`jwt`, `hasher`, `luhn`, `tx_db`, `retry`, `ttl`) |
| Blind Passing of Flawed Code | 11 tasks | 11 tasks | 6 tasks |

**Key Detection Finding**: Generic Review passed **100% of flawed initial implementations** because the visible unit tests did not exercise the hidden defects. In contrast, The Judge's challenge synthesis and hard gates successfully rejected **50.0% (6/12)** of the starting implementations before any repair was attempted.

## C. Repair-Loop Dynamics (Oracle Repair Evaluation)

When The Judge rejected an initial implementation, did the oracle repair loop produce verified success?

- **Tasks triggering repair loop**: 6 tasks
- **Repairs successfully verified as PASS**: **3 tasks** (`05_transaction_db`, `06_http_retry_client`, `07_lru_cache_ttl`)
  - In all 3 cases, `apply_fix.py` fixed the defect on Round 1, and Round 2 verification confirmed all gates passed.
- **Repairs failing post-repair verification**: **3 tasks** (`01_auth_jwt`, `09_password_hasher`, `11_luhn_validator`)
  - In all 3 cases, `apply_fix.py` modified the code, but The Judge's challenge synthesis generated tests that continued to fail on the repaired code.
  - Because the repair script was a static oracle and could not react to findings, the loop repeated for 5 rounds without progression.

## D. Final Quality & Signal Detection Metrics

Signal detection counts evaluate the final delivered verdict against the independent hidden test ground truth:

| Signal Classification | Baseline (A) | Generic Review (B) | The Judge (C) | Interpretation |
|---|---|---|---|---|
| **TRUE_PASS (TP)** | 1 | 1 | 3 | Correct code delivered with PASS verdict (Success) |
| **FALSE_PASS (FP)** | 11 | 11 | 6 | Flawed code delivered with PASS verdict (Dangerous False Confidence) |
| **TRUE_FAIL (TN)** | 0 | 0 | 0 | Flawed code correctly rejected with FAIL verdict |
| **FALSE_FAIL (FN)** | 0 | 0 | 3 | Correct code rejected with FAIL verdict (Over-rejection) |
| **ABSTAIN** | 0 | 0 | 0 | System withheld verdict |

### Comprehensive Quality Rates

| Metric | Formula | Baseline (A) | Generic Review (B) | The Judge (C) |
|---|---|---|---|---|
| **False PASS Rate** | FP / (TP + FP) | 91.7% | 91.7% | **66.7%** |
| **Unconditional False PASS Rate** | FP / Total Tasks | 91.7% | 91.7% | **50.0%** |
| **Verified Correct Delivery Rate** | TP / Total Tasks | 8.3% | 8.3% | **25.0%** |
| **Final Correct Implementation Rate** | (TP + FN) / Total Tasks | 8.3% | 8.3% | **50.0%** |
| **Precision** | TP / (TP + FP) | 8.3% | 8.3% | **33.3%** |
| **Recall (Sensitivity)** | TP / (TP + FN) | 100.0% | 100.0% | **50.0%** |
| **Specificity** | TN / (TN + FP) | 0.0% | 0.0% | **0.0%** |
| **Balanced Accuracy** | (Recall + Specificity) / 2 | 50.0% | 50.0% | **25.0%** |
| **Reliability** | (TP + TN) / Total Tasks | 8.3% | 8.3% | **25.0%** |
| **Benchmark Regression Rate** | Regressions / Total Tasks | 0.0% | 0.0% | **8.3% (1/12)** |

## E. Engineering & Resource Cost Analysis

> [!NOTE]
> **Token-Equivalent Estimates**: The Judge does NOT make LLM calls. Token metrics below are byte-count proxies
> (computed at 4 bytes ≈ 1 token-equivalent). Subprocess calls, hash operations, and wall-clock times are directly MEASURED.

| Cost Metric | Baseline (A) | Generic Review (B) | The Judge (C) | Measurement Type |
|---|---|---|---|---|
| Mean Verification Rounds | 1.00 | 1.00 | 2.25 | MEASURED |
| Mean Total Subprocess Calls | 0.00 | 1.00 | 4.50 | MEASURED |
| — Judge Sandbox Pytest Invocations | 0.0 | 0.0 | 2.25 | MEASURED |
| — Harness Instrumentation Calls | 0.0 | 1.0 | 2.25 | MEASURED |
| Mean Workspace Hash Operations | 0.0 | 0.0 | 2.25 | MEASURED |
| Mean Duration per Task (s) | 0.00s | 1.55s | 12.37s | MEASURED |
| Total Suite Duration (s) | 0.02s | 18.55s | 148.41s | MEASURED |
| Mean Input Bytes | 1969.00 B | 1969.00 B | 4864.00 B | ESTIMATED |
| Mean Output Bytes | 0.00 B | 720.00 B | 1624.00 B | ESTIMATED |
| Mean Total Token-Equivalents | 492.00 | 671.00 | 1621.00 | ESTIMATED (Byte proxy) |
| Total Suite Token-Equivalents | 5902.00 | 8057.00 | 19454.00 | ESTIMATED (Byte proxy) |

### Overhead Summary

- **Token-Equivalent Overhead Ratio**: **3.30×** vs. Baseline; **2.41×** vs. Generic Review.
- **Additional Token-Equivalents**: +13552.00 total byte proxies across 12 tasks.
- **Runtime Overhead**: +148.39s total execution time across the entire suite.

## F. Regression Analysis: Luhn Validator (`11_luhn_validator`)

> [!WARNING]
> **Confirmed Benchmark Regression**: `11_luhn_validator`
> Baseline = `TRUE_PASS` | Generic Review = `TRUE_PASS` | **The Judge = `FALSE_FAIL`**

### Causal Mechanism of the Regression
1. **The Starting Code**: Contained a boundary bug `if doubled > 10` instead of `> 9`. However, the benchmark's visible and hidden test suites did not exercise a card number with digit `5` at an odd index. Both Baseline and Generic Review therefore scored `TRUE_PASS` against the ground-truth suite.
2. **Challenge Synthesis Failure**: The Judge's property engine extracted boundary values (`1` and `10`) from source code comments and generated property tests calling `validate_luhn(1.0)` and `validate_luhn(10.0)`.
3. **Type Contract Violation**: Because `validate_luhn(card_number: str)` expects a string, passing a float raised `TypeError: 'float' object is not iterable`. This was treated as a behavioral test failure rather than an invalid test probe.
4. **Repair Loop Failure**: Even after `apply_fix.py` corrected the logic to `if doubled > 9`, the synthesized challenge tests continued to pass floats and crash with `TypeError`. The Judge failed the valid code on all 5 rounds, creating 7.53× resource overhead and degrading the result to `FALSE_FAIL`.

See [`benchmark/luhn_regression_analysis.md`](file:///c:/projects/the-judge/benchmark/luhn_regression_analysis.md) for full stack traces and reproduction scripts.

## G. Evidence Duplication & Loop Stagnation Findings

- **Trials with multi-round execution**: 6 of 12 tasks.
- **Mean Duplication Ratio (Multi-round Trials)**: **34.1%**
- **Total Repeated Bytes**: **29,557 bytes**

### Tasks Experiencing Loop Stagnation

| Task | Rounds | Duplication Ratio | Repeated Bytes | Mechanism of Duplication |
|---|---|---|---|---|
| `01_auth_jwt` | 5 | 63.0% | 16,270 B | Identical file hash for rounds 2–5; identical 10 blocking issues repeated 4 times |
| `09_password_hasher` | 5 | 66.2% | 7,392 B | Identical file hash for rounds 2–5; identical 3 blocking issues repeated 4 times |
| `11_luhn_validator` | 5 | 66.8% | 6,679 B | Identical file hash for rounds 2–5; identical synthesized TypeError repeated 4 times |

See [`benchmark/evidence_duplication_analysis.md`](file:///c:/projects/the-judge/benchmark/evidence_duplication_analysis.md) for the complete root cause analysis and recommended stagnation guards.

## H. Per-Task Outcome Matrix

| Task | Difficulty | Defect Type | GT | Baseline (A) | Generic Review (B) | The Judge (C) | Contribution Category |
|---|---|---|---|---|---|---|---|
| `01_auth_jwt` | medium | security | PASS | FALSE_PASS | FALSE_PASS | FALSE_FAIL | **DETECT_UNVERIFIED** |
| `02_api_rate_limiter` | medium | state | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | **ALL_FALSE_PASS** |
| `03_input_sanitizer` | easy | logic | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | **ALL_FALSE_PASS** |
| `04_json_schema_parser` | medium | logic | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | **ALL_FALSE_PASS** |
| `05_transaction_db` | hard | transaction | PASS | FALSE_PASS | FALSE_PASS | TRUE_PASS | **IMPROVEMENT** |
| `06_http_retry_client` | medium | retry | PASS | FALSE_PASS | FALSE_PASS | TRUE_PASS | **IMPROVEMENT** |
| `07_lru_cache_ttl` | hard | state | PASS | FALSE_PASS | FALSE_PASS | TRUE_PASS | **IMPROVEMENT** |
| `08_bounded_queue` | easy | logic | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | **ALL_FALSE_PASS** |
| `09_password_hasher` | hard | security | PASS | FALSE_PASS | FALSE_PASS | FALSE_FAIL | **DETECT_UNVERIFIED** |
| `10_inventory_refactor` | medium | state | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | **ALL_FALSE_PASS** |
| `11_luhn_validator` | easy | logic | PASS | TRUE_PASS | TRUE_PASS | FALSE_FAIL | **REGRESSION** |
| `12_tiered_discount` | medium | logic | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | **ALL_FALSE_PASS** |

### Contribution Category Definitions
- **`IMPROVEMENT` (3 tasks)**: The Judge caught the starting defect that Generic Review missed, and oracle repair achieved verified correct delivery (`transaction_db`, `http_retry_client`, `lru_cache_ttl`).
- **`REGRESSION` (1 task)**: The Judge incorrectly failed an implementation that passed all baseline and ground truth checks (`luhn_validator`).
- **`DETECT_UNVERIFIED` (2 tasks)**: The Judge correctly caught the starting defect, but rejected post-repair code due to challenge synthesis failures (`auth_jwt`, `password_hasher`).
- **`ALL_FALSE_PASS` (6 tasks)**: Defect not caught by visible tests or Judge gates (`api_rate_limiter`, `input_sanitizer`, `json_schema_parser`, `bounded_queue`, `inventory_refactor`, `tiered_discount`).

## I. Methodological Limitations

1. **Oracle Repair vs. Agent Behavior**: `apply_fix.py` is an unguided, static replacement. It does not test an agent's ability to interpret `suggested_focus` findings.
2. **Proxy Token Metrics**: The Judge makes zero LLM calls. Ratios represent source and stdout disk bytes, not LLM token pricing.
3. **Sample Size**: 12 tasks provide point estimates of capability, not statistical population estimates.
4. **Challenge Synthesis Type Rigidity**: Challenge tests that violate Python type contracts represent a verified engine vulnerability.

## J. Direct Answers to the Core Benchmark Questions

### 1. Does The Judge actually improve coding-agent results?
- **Detection**: YES. The Judge caught starting defects in **50.0% (6/12)** of tasks where Generic Review caught **0%**.
- **False Confidence Reduction**: YES. The Judge reduced the false PASS rate from **91.7%** to **66.7%** (and unconditional false passes from 91.7% to 50.0%).
- **Delivery**: MIXED. When repair succeeded, verified delivery increased from 8.3% to 25.0%. However, 1 regression occurred on `11_luhn_validator`.

### 2. How much additional token/API usage does it introduce?
- **LLM API Usage**: **Zero**. The Judge makes no LLM calls.
- **Subprocess Overhead**: The Judge averaged **2.25 sandbox subprocess calls** per task vs. 0 for Baseline and 1.0 for Generic Review.
- **Token-Equivalent Overhead**: Approximately **3.30×** baseline byte volume.
- **Wall-Clock Time**: +148.39 seconds total across 12 tasks.

### 3. Does the quality improvement justify the additional cost?
- For defects requiring behavioral boundary verification (atomicity, TTL, retry backoff), The Judge is the only condition that prevented shipping broken code.
- However, when challenge synthesis generates invalid tests, The Judge incurs 5.5× to 7.5× overhead while rejecting correct code. Stagnation guards are necessary to make this cost-effective.

### 4. Is The Judge itself efficient, or does it waste resources?
- **Efficient on Resolvable Tasks**: On tasks that pass or fix quickly (e.g. `transaction_db`, `lru_cache_ttl`), The Judge exits in 2 rounds with minimal overhead.
- **Wasteful on Stagnant Tasks**: On tasks where challenge synthesis fails repeatedly (`auth_jwt`, `password_hasher`, `luhn_validator`), The Judge wasted 63–67% of its processed bytes across 4 redundant rounds due to lack of a stagnation exit guard.

### 5. Which types of tasks benefit from it, and which do not?
- **Benefits Most**: State-dependent, transactional, and timing-dependent tasks (`05_transaction_db`, `06_http_retry_client`, `07_lru_cache_ttl`).
- **Benefits Least**: Tasks where challenge synthesis generates type-incompatible inputs for string parameters (`11_luhn_validator`).
- **Neutral**: Tasks where neither visible tests nor challenge synthesis exercised the missing edge cases (`02_api_rate_limiter`, `08_bounded_queue`, `10_inventory_refactor`).
