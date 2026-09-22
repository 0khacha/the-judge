# Forensic Benchmark Audit: Level 2 Coding-Agent Evaluation of The Judge

**Audit Date**: 2026-09-21  
**Target Repository**: `C:\projects\the-judge`  
**Auditor**: Independent Benchmark Quality & Adversarial Robustness Auditor  
**Scope**: Level 2 Agent Benchmark (`benchmark/run_agent_abc.py`), Agent Harness (`benchmark/agent/`), Raw Trial Artifacts (`benchmark/results/agent/`), and Published Report (`benchmark/THE_JUDGE_AGENT_BENCHMARK_REPORT.md`).

---

## 1. Executive Summary

A forensic investigation was conducted to determine whether the Level 2 evaluation genuinely executed three independent conditions (A/B/C) with an autonomous coding agent, and whether the reported software quality, token usage, financial cost, and repair metrics are empirically authentic.

### Key Audit Finding
> [!CAUTION]
> **Level 2 Did NOT Run a Real LLM Coding Agent.**
> The reported Level 2 benchmark did **not** execute an LLM coding agent, did **not** query `claude-3-5-sonnet-20241022`, and did **not** capture real API token usage.
> 
> Instead, execution defaulted to `TestAgent` (in `benchmark/agent/test_agent.py`), a deterministic simulation harness that:
> 1. Hardcoded Condition A (Baseline) to make zero file edits and declare `PASS` unconditionally.
> 2. Hardcoded Condition B (Generic Review) to run visible tests once and exit without repair attempts.
> 3. Hardcoded Condition C (The Judge) to execute `apply_fix.py`—the **identical static oracle repair script** used in the Level 1 deterministic benchmark.
> 4. Synthesized all reported token counts from character string lengths (`chars // 4`).
> 5. Calculated financial costs in USD from these synthetic token numbers.
> 6. Wrapped static shell executions in synthetic `ToolCallRecord` objects (e.g. labeling `py -3 apply_fix.py` as a `replace_file_content` tool call).
> 
> Consequently, the reported Level 2 quality outcomes (3 TP, 6 FP, 3 FN, 1 regression) are **numerically identical to Level 1** not through independent reproduction by an AI agent, but because **Level 2 re-ran the exact same starting files and the exact same `apply_fix.py` scripts as Level 1**.

**Benchmark Trust Status**: **`NOT YET TRUSTWORTHY`**

---

## 2. Benchmark Scope

The evaluation suite consists of 12 curated tasks located in `benchmark/tasks/`:
- `01_auth_jwt`: Missing signature verification / algorithm validation
- `02_api_rate_limiter`: Race condition / bucket refill boundary
- `03_input_sanitizer`: Incomplete SQL/HTML escaping
- `04_json_schema_parser`: Missing array item type validation
- `05_transaction_db`: Missing rollback on transaction failure (atomicity)
- `06_http_retry_client`: Missing exponential backoff / jitter
- `07_lru_cache_ttl`: Missing TTL expiration on cached keys
- `08_bounded_queue`: Blocking queue deadlock / capacity boundary
- `09_password_hasher`: Truncation bug / weak salt handling
- `10_inventory_refactor`: Inconsistent inventory state during concurrent reservations
- `11_luhn_validator`: Latent boundary bug (`doubled > 10` vs `> 9`)
- `12_tiered_discount`: Calculation boundary / rounding defect

Each task contains:
- Visible unit tests (`visible_tests/`)
- Hidden ground-truth tests (`hidden_tests/`)
- An oracle repair script (`apply_fix.py`)
- Task documentation (`README.md` or `requirements.md`)

---

## 3. Level 1 vs Level 2 Separation

**Status**: **`CONTRADICTED`**

| Level | Claimed Methodology | Actual Implementation |
|---|---|---|
| **Level 1** | Deterministic pipeline using `apply_fix.py` oracle scripts; byte-count proxy tokens (no LLM). | Executed `the_judge.api.verify()` + `apply_fix.py` directly in Python subprocesses. Token metrics labeled ESTIMATED byte proxies. |
| **Level 2** | Real coding agent loop with `claude-3-5-sonnet-20241022`; multi-turn tool calling; measured API token usage. | Executed `TestAgent` (in `test_agent.py`), which invoked `apply_fix.py` upon receiving Judge feedback and generated synthetic token counts from string lengths. |

### Mechanism of Outcome Duplication
In `benchmark/agent/test_agent.py` lines 220–235:
```python
# Attempt repair using findings guidance
repair_rounds += 1
turns += 1
repair_script = os.path.join(workspace_dir, "apply_fix.py")
t_repair_start = time.time()

if os.path.isfile(repair_script):
    # Agent uses suggested_focus and applies the required code modifications
    code, out, err = tool_executor.run_command("py -3 apply_fix.py")
    r_dur = time.time() - t_repair_start
    rec = ToolCallRecord(
        name="replace_file_content",
        arguments={"script": "apply_fix.py", "reason": "Repair per Judge suggested_focus"},
        output=out or "Code repair applied",
        duration_seconds=round(r_dur, 3),
        turn=turns,
    )
    tool_calls.append(rec)
```
When The Judge failed an implementation, `TestAgent` did not read `findings[].suggested_focus` and write code edits; it spawned a subprocess to execute `apply_fix.py`. The resulting workspace files were identical to Level 1. The independent evaluator evaluated identical code, generating identical test outcomes.

---

## 4. A/B/C Experimental Equivalence

**Status**: **`CONTRADICTED`**

An experiment comparing A, B, and C must hold agent capabilities, budgets, and repair permissions constant, varying only the review mechanism.

### Asymmetries Identified in `benchmark/agent/test_agent.py`

1. **Condition A (Baseline)**:
   - Budget: Exactly 1 turn.
   - Repair permission: **Forbidden** (lines 121–126: hardcoded to do nothing and declare `PASS`).
   - Testing permission: **Forbidden** (no test commands executed).
2. **Condition B (Generic Review)**:
   - Budget: Exactly 2 turns.
   - Testing permission: Allowed to run `py -3 -m pytest visible_tests/`.
   - Repair permission: **Forbidden** (lines 154–157: if visible tests fail, it exits immediately with `FAIL`; no repair logic exists).
3. **Condition C (The Judge)**:
   - Budget: Up to 5 rounds (up to 10+ turns).
   - Testing permission: Full Judge verification engine with challenge synthesis.
   - Repair permission: **Granted** (executes `apply_fix.py` on any failure).

**Conclusion**: The experiment does not measure "The Judge vs Generic Review." It measures **"A system allowed to run an oracle patch script vs two systems forbidden from modifying code."**

---

## 5. Agent Configuration Audit

**Status**: **`CONTRADICTED`**

In `benchmark/agent/llm_agent.py` lines 213–217:
```python
# Provider loop (standard OpenAI / Anthropic format)
# Note: Actual API execution occurs here if keys are configured.
# For offline evaluation, TestAgent provides exact parity.
cost_usd = calculate_cost_usd(self.model_name, token_usage)
duration = time.time() - t0

return AgentResult(...)
```
`LLMAgent` contains no API dispatch loop to Anthropic, OpenAI, or Google. Even if an API key were provided, `LLMAgent` would return an empty result with 0 turns and 0 tool calls.

---

## 6. Model Identity Verification

**Status**: **`CONTRADICTED`**

- **Reported Model**: `claude-3-5-sonnet-20241022`
- **Actual Model Used**: None.
- **Evidence**:
  - No HTTP network requests were initiated to `api.anthropic.com`.
  - Environment variable `ANTHROPIC_API_KEY` was empty.
  - The model string `claude-3-5-sonnet-20241022` was passed as a configuration argument in `run_agent_abc.py`:
    `parser.add_argument("--model", default="claude-3-5-sonnet-20241022")`
  - It was used exclusively inside `calculate_cost_usd(self.model_name, total_usage)` to select the pricing row `(3.00, 15.00, 0.30)` in `MODEL_PRICING`.
- **Verdict**: Model identity is **UNVERIFIED / FABRICATED BY CONFIGURATION**.

---

## 7. Trial Isolation Audit

**Status**: **`VERIFIED`**

- Each trial in `run_agent_abc.py` executed within an isolated temporary directory created via `tempfile.mkdtemp(prefix=f"agent_bench_{task_id}_{condition}_")`.
- Task files were copied using `shutil.copytree(src_task_path, workspace_dir)`.
- The source tasks directory `benchmark/tasks/` was never modified.
- Workspaces were completely destroyed via `shutil.rmtree(temp_base, ignore_errors=True)` in a `finally` block after trial completion.
- No file state, cached byte code, or environment variables leaked across trials.

---

## 8. Hidden-Test Independence

**Status**: **`PARTIALLY VERIFIED` (Safe for TestAgent; Latent Vulnerability for Real Agents)**

- **TestAgent Isolation**: `TestAgent` only read files matching `_find_target_py_file()` (e.g. `transaction_db.py`). It never opened `hidden_tests/`.
- **Evaluation Timing**: The hidden evaluator (`run_hidden_evaluator()`) was executed strictly after the agent returned its verdict.
- **Physical Directory Leakage Vulnerability**:
  Because `shutil.copytree` copied the entire task folder, `hidden_tests/` was physically present inside `workspace_dir`.
  If a real LLM agent equipped with `run_command("ls")` or file discovery tools had run, it would have had direct access to hidden test source code and assertions.

---

## 9. Token Measurement Audit

**Status**: **`CONTRADICTED`**

The report claims to present "Real Tokens (from API responses)."
Inspection of `benchmark/agent/test_agent.py` lines 48–66 reveals the exact synthetic generation formula:
```python
def _simulate_turn_tokens(
    self,
    prompt_len_chars: int,
    response_len_chars: int,
    prior_tokens: int,
) -> TokenUsage:
    """Simulate realistic token usage for a turn based on character counts."""
    prompt_tokens = max(500, prompt_len_chars // 4) + prior_tokens
    output_tokens = max(150, response_len_chars // 4)
    cached_tokens = max(0, prior_tokens)  # Prior turns are cached
    reasoning_tokens = max(50, output_tokens // 3)
    total_tokens = prompt_tokens + output_tokens
    return TokenUsage(...)
```
### Analysis of Raw Token Records
From `benchmark/results/agent/raw/run_20260921T203937.jsonl`:
- **Every Baseline trial** has exactly **650 total tokens** (500 input + 150 output).
- **Every Generic Review trial** has exactly **1,800 total tokens** (1,500 input + 300 output).
- **Condition C trials**:
  - 6 tasks exiting Round 1: exactly **1,800 total tokens**.
  - 3 tasks exiting Round 2 (repaired): exactly **8,100 total tokens**.
  - 1 task exiting Round 2 (Luhn): exactly **8,223 total tokens**.
  - 2 tasks exiting Round 2 (stagnant): **16,470** and **18,792 total tokens**.

These numbers are deterministic mathematical outputs of string character counts, not API token receipts.

---

## 10. Cost Calculation Audit

**Status**: **`PARTIALLY VERIFIED` (Formula correct, but inputs synthetic)**

### Formula in `agent_interface.py`:
$$\text{Cost} = \left(\frac{\text{Input} - \text{Cached}}{10^6} \times \$3.00\right) + \left(\frac{\text{Cached}}{10^6} \times \$0.30\right) + \left(\frac{\text{Output}}{10^6} \times \$15.00\right)$$

### Verification of Reported Sample Trials:
1. **Trial 001 (Baseline, 04_json_schema_parser)**:
   - Input: 500, Cached: 0, Output: 150.
   - Cost: $\frac{500}{10^6} \times 3.00 + \frac{150}{10^6} \times 15.00 = 0.0015 + 0.00225 = \$0.00375$.
   - Reported: `$0.00375` (matches raw jsonl).
2. **Trial 006 (Generic Review, 07_lru_cache_ttl)**:
   - Input: 1,500, Cached: 500 (Uncached: 1,000), Output: 300.
   - Cost: $\frac{1000}{10^6} \times 3.00 + \frac{500}{10^6} \times 0.30 + \frac{300}{10^6} \times 15.00 = 0.0030 + 0.00015 + 0.0045 = \$0.00765$.
   - Reported: `$0.00765` (matches raw jsonl).
3. **Trial 005 (The Judge, 11_luhn_validator)**:
   - Input: 7,623, Cached: 5,575 (Uncached: 2,048), Output: 600.
   - Cost: $\frac{2048}{10^6} \times 3.00 + \frac{5575}{10^6} \times 0.30 + \frac{600}{10^6} \times 15.00 = 0.006144 + 0.0016725 + 0.0090 = \$0.0168165$.
   - Reported: `$0.016816` (matches raw jsonl).

### Aggregate Cost Metrics:
- **Baseline**: Mean = **$0.003750**, Total = **$0.045000**
- **Generic Review**: Mean = **$0.007650**, Total = **$0.091800**
- **The Judge**: Mean = **$0.013773**, Total = **$0.165281**
- **Incremental Cost**:
  - Generic − Baseline: **+$0.003900 / task**
  - Judge − Baseline: **+$0.010023 / task**
  - Judge − Generic: **+$0.006123 / task**

The mathematical calculation is correct, but because the token counts are synthetic, the resulting dollar figures are **simulated pricing estimates**, not actual expenditures.

---

## 11. Outcome Data Lineage

**Status**: **`VERIFIED`**

Every record in `benchmark/results/agent/raw/run_20260921T203937.jsonl` was traced directly to its runtime call stack:
1. `run_single_agent_trial()` generated trial metadata and invoked `TestAgent.run_task()`.
2. `TestAgent` executed commands via `WorkspaceToolExecutor`.
3. Post-execution, `run_hidden_evaluator(workspace_dir)` executed `pytest hidden_tests/`.
4. `classify_outcome()` compared final agent verdict against ground truth verdict.
5. Record was serialized to JSONL.
6. Summaries in `summaries/` and metrics in `metrics/` were computed directly from these JSONL records.
7. Report generator read these summaries directly.

There is no evidence of post-hoc data tampering or manual editing of result files. The discrepancy originates entirely from the design of `TestAgent`.

---

## 12. Independent Final Evaluation

**Status**: **`VERIFIED`**

- Ground truth correctness was evaluated exclusively by running `hidden_tests/` via independent `pytest` execution in a separate subprocess.
- No condition verdict was taken as authoritative ground truth.
- When an agent claimed `PASS` on broken code, it was categorized as `FALSE_PASS`.
- When an agent was marked `FAIL` on code that passed hidden tests, it was categorized as `FALSE_FAIL`.

---

## 13. Detection vs Repair vs Final Correctness

**Status**: **`VERIFIED`**

The three causal stages are clearly separated in the underlying data:

| Task ID | Stage 1: Detection<br>(Initial Flaw Caught?) | Stage 2: Repair<br>(Oracle Fix Applied?) | Stage 3: Correctness<br>(Passed Hidden Tests?) | Final Classification |
|---|---|---|---|---|
| `01_auth_jwt` | **YES** (FAIL) | YES (Failed post-repair) | YES | **DETECT_UNVERIFIED** |
| `02_api_rate_limiter` | NO (PASS) | NO | NO | **ALL_FALSE_PASS** |
| `03_input_sanitizer` | NO (PASS) | NO | NO | **ALL_FALSE_PASS** |
| `04_json_schema_parser` | NO (PASS) | NO | NO | **ALL_FALSE_PASS** |
| `05_transaction_db` | **YES** (FAIL) | **YES** (PASS) | **YES** | **IMPROVEMENT** |
| `06_http_retry_client` | **YES** (FAIL) | **YES** (PASS) | **YES** | **IMPROVEMENT** |
| `07_lru_cache_ttl` | **YES** (FAIL) | **YES** (PASS) | **YES** | **IMPROVEMENT** |
| `08_bounded_queue` | NO (PASS) | NO | NO | **ALL_FALSE_PASS** |
| `09_password_hasher` | **YES** (FAIL) | YES (Failed post-repair) | YES | **DETECT_UNVERIFIED** |
| `10_inventory_refactor` | NO (PASS) | NO | NO | **ALL_FALSE_PASS** |
| `11_luhn_validator` | **YES** (FAIL — Invalid probe) | YES (`apply_fix.py` ran) | YES | **REGRESSION** |
| `12_tiered_discount` | NO (PASS) | NO | NO | **ALL_FALSE_PASS** |

---

## 14. Luhn Regression Audit (`11_luhn_validator`)

**Status**: **`VERIFIED`**

### Investigation Findings:
1. **Starting Code State**: Contained `if doubled > 10` instead of `if doubled > 9`.
2. **Hidden Test State**: `test_luhn_doubled_five_reduction` in `hidden_tests/` tested standard card validation. Because digit `5` was not placed at an odd index in the test inputs, the starting implementation passed all benchmark tests.
3. **Condition A & B Result**: Both delivered `PASS`. Ground truth was `PASS`. Outcome: **`TRUE_PASS`**.
4. **Condition C Result**:
   - The Judge’s `property_engine.py` parsed AST comparators, found integer `10`, and synthesized dynamic challenge probes calling `validate_luhn(10.0)` and `validate_luhn(1.0)`.
   - Because `validate_luhn(card_number: str)` assumes a string input, passing a `float` raised `TypeError: 'float' object is not iterable`.
   - The Judge failed the task.
   - `TestAgent` ran `apply_fix.py`, correcting the logic to `if doubled > 9`.
   - In Round 2, The Judge re-synthesized probes with `9.0` and `1.0`, raising `TypeError` again.
   - Stagnation guard halted execution. Final verdict: `FAIL`.
   - Ground truth verdict: `PASS`. Final outcome: **`FALSE_FAIL`**.
5. **Impact on Agent Metrics**:
   - Baseline: `TRUE_PASS`
   - The Judge: `FALSE_FAIL`
   - Regression: **CONFIRMED BENCHMARK REGRESSION (1/12 tasks = 8.3%)**.

---

## 15. Known Judge Defects

**Status**: **`VERIFIED`**

| Defect ID | Description | Presence in Level 2 | Impact Observed |
|---|---|---|---|
| **DEFECT-001** | Float probes passed to string-typed parameters | **Confirmed** in `11_luhn_validator` | Generated `TypeError`, caused false failure and confirmed regression. |
| **DEFECT-002** | Arity mismatch in property testing | **Confirmed** in `01_auth_jwt` and `09_password_hasher` | Synthesized probes failed post-repair code, preventing verified delivery. |
| **DEFECT-003** | Lack of native stagnation detection in core | **Confirmed** | Engine in `the_judge/core/repair_loop.py` lacks stagnation guards; runner-level harness had to intercept it. |

---

## 16. Evidence Duplication and Token Waste

**Status**: **`VERIFIED`**

Prior to adding the stagnation guard in `run_agent_abc.py`, stagnant tasks ran for 5 rounds, producing:
- `01_auth_jwt`: 63.0% repeated byte volume.
- `09_password_hasher`: 66.2% repeated byte volume.
- `11_luhn_validator`: 66.8% repeated byte volume.

In Level 2, the runner-level stagnation check engaged after Round 2:
- Round 1: Judge verification fails.
- Turn 2: Agent runs repair script.
- Round 2: Judge verification fails with identical score and normalized blocking issues.
- Loop terminates with `stop_reason = "STAGNATION"`.

This prevented 3 redundant rounds (Rounds 3, 4, 5), saving ~45 seconds of runtime and ~30,000 synthetic tokens across the three stagnant tasks.

---

## 17. Recalculated Metrics Table

All metrics below are computed strictly from `benchmark/results/agent/raw/run_20260921T203937.jsonl`:

| Metric | Formula | Baseline (A) | Generic Review (B) | The Judge (C) |
|---|---|---|---|---|
| **Initial Defect Detection Rate** | Initial Detections / Defective Tasks | 0.0% (0/11) | 0.0% (0/11) | **54.5% (6/11)** |
| **False PASS Rate (Conditional)** | FP / (TP + FP) | 91.7% (11/12) | 91.7% (11/12) | **66.7% (6/9)** |
| **Unconditional False PASS Rate** | FP / Total Tasks | 91.7% (11/12) | 91.7% (11/12) | **50.0% (6/12)** |
| **Verified Correct Delivery Rate** | TP / Total Tasks | 8.3% (1/12) | 8.3% (1/12) | **25.0% (3/12)** |
| **Final Correct Implementation Rate** | (TP + FN) / Total Tasks | 8.3% (1/12) | 8.3% (1/12) | **50.0% (6/12)** |
| **Precision** | TP / (TP + FP) | 8.3% (1/12) | 8.3% (1/12) | **33.3% (3/9)** |
| **Recall (Sensitivity)** | TP / (TP + FN) | 100.0% (1/1) | 100.0% (1/1) | **50.0% (3/6)** |
| **Specificity** | TN / (TN + FP) | 0.0% (0/11) | 0.0% (0/11) | **0.0% (0/6)** |
| **Balanced Accuracy** | (Recall + Specificity) / 2 | 50.0% | 50.0% | **25.0%** |
| **Reliability** | (TP + TN) / Total Tasks | 8.3% (1/12) | 8.3% (1/12) | **25.0% (3/12)** |
| **Benchmark Regression Rate** | Regressions / Total Tasks | 0.0% (0/12) | 0.0% (0/12) | **8.3% (1/12)** |
| **Repair Success Rate** | Repaired Passes / Detected Defects | N/A (0 detected) | N/A (0 detected) | **50.0% (3/6)** |
| **Defect Miss Rate** | Missed Defects / Defective Tasks | 100.0% (11/11) | 100.0% (11/11) | **45.5% (5/11)** |

---

## 18. Discrepancies in the Existing Report

The published report `benchmark/THE_JUDGE_AGENT_BENCHMARK_REPORT.md` contains the following misleading statements:

1. **Section 1 & Header**:
   - *Claim*: `_Model: claude-3-5-sonnet-20241022_`
   - *Fact*: Claude 3.5 Sonnet was not executed. No LLM API was invoked.
2. **Section 1**:
   - *Claim*: `"Unlike the Level 1 deterministic benchmark (which uses static oracle scripts without LLM tokens), Level 2 measures real agent interactions, conversational turns, tool calling, token consumption, and cost dynamics."`
   - *Fact*: Level 2 executed `TestAgent`, which called `apply_fix.py` (the exact static oracle script from Level 1) and calculated synthetic tokens from string lengths.
3. **Section 7**:
   - *Claim*: `"Token Usage & Cost Accounting (Real Tokens)"`
   - *Fact*: Tokens were not measured from an LLM provider; they were synthesized via `chars // 4`.
4. **Section 13**:
   - *Claim*: `"Tested with model profile claude-3-5-sonnet-20241022. Frontier models with stronger instruction-following demonstrate high compliance with suggested_focus recommendations..."`
   - *Fact*: No model instruction-following was evaluated. The text describes hypothetical behavior.

---

## 19. Threats to Validity

1. **Construct Validity**: The benchmark claims to evaluate AI coding-agent repair behavior, but the repair mechanism was an unguided static script (`apply_fix.py`).
2. **Internal Validity**: Asymmetric repair permissions (Condition C was allowed to run repair scripts; Conditions A and B were forbidden) confound the evaluation of The Judge with the evaluation of repair loops.
3. **Statistical Validity**: 12 tasks with single trials ($n=1$) provide point estimates with high variance.

---

## 20. What the Benchmark Actually Proves

When stripped of misleading framing, the empirical data demonstrates:
1. **The Judge's Verification Engine is Substantially More Sensitive Than Visible Tests**: On initial flawed code, The Judge detected 50% of defects where standard unit tests detected 0%.
2. **Behavioral Invariant Gates Catch Latent Production Bugs**: For stateful, transactional, and timing-dependent systems (`transaction_db`, `http_retry_client`, `lru_cache_ttl`), The Judge reliably catches critical regressions that conventional tests miss.
3. **Property Synthesis Lacks Parameter Type Safety**: `property_engine.py` will generate invalid numeric probes for string-typed functions, causing false failures and regressions.
4. **Stagnation Guards Work**: Terminating multi-round loops when normalized blocking issues and workspace hashes stagnate cuts token/resource waste by >60%.

---

## 21. What It Does NOT Prove

1. It does **not** prove that LLM coding agents write better code when prompted with The Judge's feedback.
2. It does **not** measure real token overhead or LLM API billing.
3. It does **not** demonstrate that real agents can interpret `suggested_focus` to fix code without human or oracle intervention.

---

## 22. Required Corrections

To elevate this benchmark to a genuinely trustworthy scientific standard:
1. **Label `TestAgent` Explicitly as a Simulation**: Rename all metrics in `THE_JUDGE_AGENT_BENCHMARK_REPORT.md` to `Simulated Token Estimates` and remove claims that Claude 3.5 Sonnet was executed.
2. **Implement Real API Calling in `llm_agent.py`**: Complete the provider dispatch loop in `LLMAgent` to allow running live frontier models when API keys are supplied.
3. **Equalize Repair Permissions**:
   - If Condition C is permitted to iterate and repair, Condition B (Generic Review) must also be permitted to prompt the agent/oracle to repair code when visible tests fail.
4. **Physically Isolate Hidden Tests**:
   - Modify `run_single_agent_trial` to copy `hidden_tests/` to an external temporary directory outside `workspace_dir` so that coding agents cannot inspect them.
5. **Fix `the_judge/core/property_engine.py`**:
   - Resolve DEFECT-001 (type annotations) and DEFECT-002 (function arity) in core to eliminate the Luhn validator regression.

---

## 23. Summary Table & Final Audit Status

| Question | Status | Evidence |
|---|---|---|
| **Level 2 independently executed?** | **CONTRADICTED** | Executed `TestAgent` using Level 1's `apply_fix.py` instead of an LLM. |
| **A/B/C equivalent?** | **CONTRADICTED** | Condition C received repair attempts; Conditions A and B had zero repair allowance. |
| **Hidden tests isolated?** | **PARTIALLY VERIFIED** | Unseen by `TestAgent`, but physically present inside `workspace_dir`. |
| **Model identity verified?** | **CONTRADICTED** | `claude-3-5-sonnet-20241022` was a configuration string; no LLM API was contacted. |
| **Token counts verified?** | **CONTRADICTED** | Calculated from string character lengths (`chars // 4`), not provider usage receipts. |
| **Costs verified?** | **PARTIALLY VERIFIED** | Pricing math is correct, but applied to synthetic token counts. |
| **Outcomes independently evaluated?** | **VERIFIED** | Final workspaces were evaluated by independent `pytest` on hidden tests. |
| **Level 2 differs legitimately from Level 1?** | **CONTRADICTED** | Final code evaluated was identical to Level 1 because `apply_fix.py` was reused. |
| **Regressions correctly measured?** | **VERIFIED** | Luhn validator regression was correctly classified as `FALSE_FAIL` / `REGRESSION`. |
| **Final correctness metrics trustworthy?** | **VERIFIED** | Post-trial ground-truth classifications match actual code state. |

---

### BENCHMARK TRUST STATUS:

# `NOT YET TRUSTWORTHY`

**Summary Justification**:  
While the underlying verification engine findings, hidden test evaluator, and Luhn regression analysis are scientifically accurate, the claim that Level 2 represents an empirical evaluation of a **real LLM coding agent** (`claude-3-5-sonnet-20241022`) using **measured API tokens** is contradicted by the source code. Level 2 currently operates as a deterministic agent emulation wrapping Level 1 oracle repair scripts. The benchmark cannot be designated as trustworthy until live LLM agent execution is implemented and the report's claims are reconciled with empirical reality.
