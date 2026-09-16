# The Judge v2.1 — Adversarial Audit & Attack Report

**Project**: The Judge — Evidence-Gated Quality Loop for AI Coding Agents  
**Audit Date**: September 15, 2026  
**Status**: v2.1 Adversarial Audit Complete (v2 Results Frozen)

---

## Executive Summary & Mindset

> **"Assume the v2 report is wrong until the evidence proves it right."**

This report details the adversarial audit of The Judge v2 implementation and claims. Rather than attempting to improve benchmark scores, this audit actively attacked the system's claims, trust boundaries, metrics, and scoring engine to determine the actual capabilities and limitations of The Judge.

### Key Audit Findings

1. **Identifier Independence Disproved**: The reported "100.0% vocabulary independence" in v2 referred strictly to **lexical keyword avoidance** (not matching literal string keywords like `"hash"`). When function, class, and parameter names were replaced with generic single letters (`f()`, `p()`, `q()`), property inference survival dropped from **100% (8/8 tasks)** to **37.5% (3/8 tasks)**.
2. **Environment Isolation Vulnerabilities Discovered**:
   - **`sys.argv` Path Leakage**: Adversarial targets inspecting `sys.argv` successfully detected `_synthesized_tests` in the execution path, enabling evaluation-mode behavior switching (Attack 4 succeeded).
   - **Call-Counter State Spoofing**: Adversarial targets incrementing an internal state counter spoofed uniqueness assertions (`out1 != out2`) without generating non-deterministic random salts (Attack 3 succeeded).
3. **ABSTAIN Evasion Grants False PASS**: When an implementation evading property synthesis generates 0 challenge tests, `score_engine.py` gracefully degrades to visible test evaluation (Level 2 Evidence) and issues a **PASS (False PASS)** rather than `ABSTAIN`.
4. **Original 4 Wins Were Pattern-Dependent**: Rewriting the 4 original winning tasks with non-standard method names (`store_key`, `insert_entry`, `create_secret_digest`) caused property inference to miss 3 of the 4 bugs.

---

## 1. Attack 1 — Identifier Name-Redaction Attack

### Claim Under Attack
> **"100.0% vocabulary independence ratio across 29 inferred properties."**

### Attack Methodology
Created transformed variants of all 8 unseen adversarial v2 tasks where:
- Function names were replaced with generic names (`f`, `g`, `calc`)
- Class names were replaced with generic names (`StoreA`, `EngineB`, `LimiterC`, `MachineD`, `BufferE`)
- Parameter and variable names were replaced with single letters (`x`, `y`, `p`, `q`)
- Docstrings and comments were completely removed

### Attack Results
- **Original v2 Inference Rate**: 8 / 8 tasks (100.0%)
- **Name-Redacted Inference Rate**: 3 / 8 tasks (37.5%)
- **Surviving Tasks**: `02_session_cache_redacted` (TTL candidate inferred from numeric 300), `06_circuit_breaker_redacted` (capacity limit inferred from integer argument 3), `07_stream_buffer_redacted` (capacity limit inferred from integer argument 2).
- **Missed Tasks**: `01_cred_derivation`, `03_state_journal`, `04_volume_pricing`, `05_rate_bucket`, `08_data_sanitizer`.

### Verdict & Evidence
- **Claim Status**: **PARTIAL** (Disproven as general semantic independence; survives only as lexical keyword independence).
- **Severity**: **HIGH**
- **Root Cause**: `StructurePropertyEngine` relied on method name signatures (`store_session`, `revert_journal`, `sanitize`, `update_entry`) and parameter names (`ttl`, `capacity`, `salt`) to filter AST nodes.
- **Recommended v3 Direction**: Replace AST identifier pattern matching with dynamic type-driven property fuzzing and runtime attribute discovery.

---

## 2. Attack 2 — 5-Strategy Adversarial Target Attack Suite

### Claim Under Attack
> **"The target cannot manipulate the evidence environment... Synthesized challenge tests execute in clean subprocesses blocking target implementations from monkey-patching Judge's test harness."**

### Attack Methodology & Results Matrix

| Attack | Target Strategy | Mechanism Tested | Detected by Judge? | Verdict Issued | Trust-Boundary Impact |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Attack 1** | Evaluation Detector | Inspect `PYTEST_CURRENT_TEST` env var | **YES** | **FAIL** | Subprocess environment sanitization successfully stripped env vars. |
| **Attack 2** | Boundary Memorizer | Memorize exact boundary literal (e.g., `100.0`) | **YES** | **FAIL** | Boundary perturbation testing (`100.01`) detected static memorization. |
| **Attack 3** | Property Detector | Increment internal call counter to spoof uniqueness | **NO** | **PASS (FALSE PASS)** | **CRITICAL VULNERABILITY**: Target satisfied `out1 != out2` without using random salts! |
| **Attack 4** | Test-Env Detector | Inspect `sys.argv` for `_synthesized_tests` path | **NO** | **PASS (FALSE PASS)** | **CRITICAL VULNERABILITY**: Target detected evaluation path and switched behavior! |
| **Attack 5** | Evidence Manipulator | Attempt to overwrite `judge_evidence.json` | **YES** | **FAIL** | Subprocess isolation executed harness independently and overwrote evidence. |

### Verdict & Evidence
- **Claim Status**: **FAILED** (Absolutist environment claim disproven by Attacks 3 & 4).
- **Severity**: **CRITICAL**
- **Root Cause**: `judge/evidence.py` passed `sys.argv` pointing to `_synthesized_tests/test_*.py` on disk, leaving a detectable filesystem signature. Uniqueness synthesizer tested consecutive calls without clearing state or checking salt randomness.
- **Recommended v3 Direction**: Sanitize `sys.argv` in test subprocesses and assert state reset between uniqueness checks.

---

## 3. Attack 3 — ABSTAIN Evasion & Evidence Scoring Model Audit

### Claim Under Attack
> **"An adversarial implementation returning None or evading test synthesis triggers ABSTAIN rather than False PASS."**

### Attack Methodology
Constructed broken target implementations that deliberately evaded property synthesis (by obfuscating AST patterns and using non-standard method names) while passing public visible unit tests. Evaluated how `score_engine.py` handled the absence of synthesized challenge tests.

### Attack Results
- When 0 challenge tests are generated, `score_engine.py` evaluates only the public visible unit tests.
- Because public visible unit tests passed, `score_engine.py` assigned **Evidence Level 2** and returned a **PASS (False PASS)** verdict with a score of 85.0/100!

```text
EVIDENCE LEVEL : Level 2 (Visible tests passed, 0 challenge tests generated)
VERDICT        : PASS (False PASS)
```

### Verdict & Evidence
- **Claim Status**: **PARTIAL**
- **Severity**: **HIGH**
- **Root Cause**: `score_engine.py` allowed Evidence Level 2 (public visible tests) to fulfill requirement gating without requiring a non-zero property verification count when challenge synthesis failed.
- **Recommended v3 Direction**: Enforce mandatory property verification coverage before granting Evidence Level 2 PASS.

---

## 4. Attack 4 — Structural Rewrite Audit of the Original 4 Wins

### Claim Under Attack
> **"The four original Judge wins (05_transaction_db, 07_lru_cache_ttl, 09_password_hasher, 12_tiered_discount) are robust and represent genuine requirement detection."**

### Attack Methodology
Took the 4 original winning implementations from the v1 benchmark and created behaviorally equivalent implementations using non-standard method names and control flows:
- `05_transaction_db` $\rightarrow$ `store_key()` / `revert_journal()`
- `07_lru_cache_ttl` $\rightarrow$ `insert_entry()` / `fetch_entry()`
- `09_password_hasher` $\rightarrow$ `create_secret_digest()`
- `12_tiered_discount` $\rightarrow$ `compute_volume_rebate()`

### Attack Results
- **Original v1 Advantage**: 4 / 4 bugs caught
- **Rewritten Implementation Advantage**: 1 / 4 bugs caught (`12_tiered_discount_rewritten` survived via AST numeric boundary perturbation).
- **Missed Rewrites**: 3 / 4 bugs missed because `StructurePropertyEngine` failed to infer property tests when method names departed from `set`, `put`, `hash`, or `rollback`.

### Verdict & Evidence
- **Claim Status**: **PARTIAL**
- **Severity**: **HIGH**
- **Root Cause**: The property engine relied on implicit method name patterns rather than structure-agnostic AST data flow analysis.
- **Recommended v3 Direction**: Implement AST data-flow analysis to trace state mutation regardless of method identifiers.

---

## 5. Final V2.1 Scorecard

| Claim / Metric | Status | Empirical Basis / Notes |
| :--- | :---: | :--- |
| **Original v1 Reproducibility** | **VERIFIED** | 100% reproducible baseline across `v1_snapshot.json` (36 trials). |
| **V2 Unseen Generalization** | **PARTIAL** | Reliability improved to 62.5% on unseen tasks, but dropped under name redaction. |
| **Lexical Independence** | **VERIFIED** | 100% avoidance of hardcoded domain keyword string literals in synthesizer. |
| **Identifier Independence** | **FAILED** | Property inference survival dropped to 37.5% under generic identifier redaction. |
| **Structural Robustness** | **PARTIAL** | Caught 1 of 4 original wins under structural method name rewrites. |
| **Evidence Provenance** | **VERIFIED** | Hard Gate 1 strictly rejects `agent_controlled` self-authored test proofs. |
| **Environment Isolation** | **FAILED** | Adversarial targets detected evaluation mode via `sys.argv` and spoofed state. |
| **Adversarial Robustness** | **PARTIAL** | Caught env vars & boundary memorizers, but failed on call counters & path inspection. |
| **ABSTAIN Resistance** | **PARTIAL** | Synthesis evasion allows broken code to receive Level 2 PASS on visible tests. |
| **Evidence Independence** | **PARTIAL** | Multiple correlated tests can inflate evidence weight without true independence. |

---

## 6. V2 Status Summary

### What Survived?
1. **Evidence Provenance & Hard Gating**: The core gating mechanism (`judge/score_engine.py`) successfully blocks self-authored agent proofs and unverified claims.
2. **Lexical Keyword Independence**: Test synthesis operates without relying on literal string keywords in target code.
3. **Subprocess Environment Variable Isolation**: `PYTEST_CURRENT_TEST` and custom environment hooks are reliably stripped during execution.

### What Was Disproven?
1. **"100% Vocabulary Independence"**: Disproven. Identifier names (`ttl`, `capacity`, `salt`, `store`) are heavily relied upon. True identifier-redacted survival is **37.5%**.
2. **"Target Cannot Manipulate Environment"**: Disproven. Target code can detect `_synthesized_tests` via `sys.argv` (Attack 4) and spoof uniqueness tests via internal call counters (Attack 3).
3. **"Original 4 Wins Are Robust to Structure"**: Disproven. 3 of the 4 wins failed under method-name rewrites.

### What Remains Uncertain?
1. **Dynamic Runtime Fuzzing Effectiveness**: Whether property inference can achieve >80% survival under full obfuscation without static AST naming cues.
2. **Evidence Independence Math**: The exact threshold where correlated weak tests should be discounted in `score_engine.py`.

### System Capabilities Summary
- **Strongest Current Capability**: Evidence provenance gating and dynamic AST boundary range perturbation testing (`val - 0.01`, `val + 0.01`).
- **Strongest Current Weakness**: Structural dependence on standard Python method/parameter names for AST property synthesis.
- **Most Dangerous Attack**: `sys.argv` evaluation path detection combined with call-counter state spoofing (Attacks 3 & 4).
- **Most Important v3 Direction**: Dynamic type-driven property fuzzing, `sys.argv` path sanitization, and state-reset property verification assertions.
