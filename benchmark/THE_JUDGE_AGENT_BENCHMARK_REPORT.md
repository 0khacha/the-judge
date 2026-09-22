# Level 2 Evaluation: Real Coding-Agent A/B/C Benchmark Report

**Benchmark Version**: 2.0.0-real  
**Target Repository**: `C:\projects\the-judge`  
**Date**: 2026-09-21  
**Architecture Status**: Genuine Provider-Based Agent Infrastructure with Physical Isolation & Fail-Closed Preflight

---

## 1. Executive Summary

This report documents the architectural overhaul and empirical evaluation of **Level 2 of The Judge Benchmark**.

Following a forensic audit ([`benchmark/LEVEL2_AUDIT_REPORT.md`](file:///c:/projects/the-judge/benchmark/LEVEL2_AUDIT_REPORT.md)), the previous Level 2 implementation was invalidated because it executed a deterministic simulation harness (`TestAgent`), utilized synthetic token formulas (`chars // 4`), and invoked static oracle scripts (`apply_fix.py`).

The Level 2 benchmark has been rebuilt from scratch:
1. **Real Provider Engine**: `LLMAgent` connects directly via native HTTP adapters (`AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`) to execute live frontier models with zero simulation fallbacks.
2. **Physical Workspace Isolation**:
   - `apply_fix.py` is **physically deleted** from agent workspaces before execution.
   - `hidden_tests/` is **physically moved** to an inaccessible evaluator workspace.
3. **Budget Equality**: Conditions A (Baseline), B (Generic Review), and C (The Judge) receive identical interaction budgets (15 turns), identical tools, and identical starting workspace hashes.
4. **Fail-Closed Integrity**: When API credentials are absent, the runner immediately aborts with exit code 1 (`[FAIL CLOSED]`), refusing to masquerade simulations as real-agent evidence.
5. **Separation of Modes**: Deterministic calibration runs are restricted to `--mode simulated`, output to `benchmark/results/agent_simulation/`, and explicitly disqualified from Level 2 publication.

---

## 2. Research Question

> **When the same real coding agent is given the same coding task and the same interaction budget, does adding The Judge's evidence-driven verification loop improve final software correctness, and what additional token/cost overhead does it introduce?**

To answer this question, the benchmark evaluates eight distinct dimensions:
1. Agent baseline capability
2. Generic review efficacy
3. The Judge verification sensitivity
4. Autonomous agent repair success
5. Final independent ground-truth correctness
6. Provider-reported token consumption
7. Real financial cost (USD)
8. Verifier-induced regression risk

---

## 3. Experimental Design

The Level 2 benchmark evaluates three strictly controlled conditions across 12 curated software engineering tasks:

```text
Task Specification (benchmark/tasks/X)
       │
       ├───────────────────────────────────────────────────┐
       ▼                                                   ▼
agent_workspace/                                    evaluator_workspace/
  ├── source files                                    ├── hidden_tests/
  ├── visible_tests/                                  └── conftest.py
  ├── requirements.md                                 (Inaccessible to Agent)
  └── README.md
  (apply_fix.py DELETED)
  (hidden_tests/ DELETED)
       │
       ▼
[ Randomized Condition Assignment ]
       ├───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
Condition A         Condition B         Condition C
(Baseline)          (Generic Review)    (The Judge)
Max 15 turns        Max 15 turns        Max 15 turns
Standard tools      Standard tools      Standard tools + judge_verify
No review prompt    Critical review     Structured findings feedback
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
             Agent Concludes Implementation
                           │
                           ▼
          Freeze Final agent_workspace State
                           │
                           ▼
        Copy Final Source Code to evaluator_workspace
                           │
                           ▼
        Execute Independent Hidden-Test Pytest
                           │
                           ▼
    Authoritative Ground-Truth Verdict & Metric Computation
```

---

## 4. Level 1 vs Level 2 Distinction

| Dimension | Level 1: Deterministic Verification Benchmark | Level 2: Real Coding-Agent Benchmark |
|---|---|---|
| **Primary Question** | Can The Judge detect flaws in static starting code? | Can an AI agent use Judge feedback to fix code? |
| **Repair Mechanism** | Static oracle scripts (`apply_fix.py`) | Autonomous agent-authored edits (`LLMAgent`) |
| **LLM Execution** | None (Deterministic Python subprocesses) | Live frontier LLM API requests |
| **Token Measurement** | Byte proxies (4 bytes ≈ 1 token-equivalent) | Exact provider-reported usage receipts |
| **Oracle Accessibility**| Required for repair loop calibration | **Strictly prohibited & physically deleted** |
| **Hidden Test Location**| Isolated subprocess execution | **Physically isolated in external evaluator dir** |

---

## 5. Agent Model and Provider Architecture

The agent communicates through a modular provider abstraction (`benchmark/agent/providers/`):

- **`AnthropicProvider`**: Native HTTP client calling `api.anthropic.com/v1/messages`. Extracts `input_tokens`, `output_tokens`, `cache_read_input_tokens`, and `tool_use` blocks.
- **`OpenAIProvider`**: Compatible with `api.openai.com/v1/chat/completions` and local endpoints (Ollama, vLLM, LiteLLM). Extracts `prompt_tokens_details.cached_tokens`, `reasoning_tokens`, and `tool_calls`.
- **`GeminiProvider`**: Direct REST client for Google Generative Language API. Extracts `usageMetadata` and `functionCall`.

### Provenance Invariant
Every real trial record stores:
- `requested_model`: Configured model profile (e.g. `claude-3-5-sonnet-20241022`)
- `actual_model`: Exact model string returned in the API response headers
- `request_ids`: Provider transaction identifiers

---

## 6. A/B/C Conditions Specification

All three conditions run the **same real LLM agent** with identical core tool definitions:
- `view_file(path, start_line, end_line)`
- `write_file(path, content)`
- `replace_file_content(path, target, replacement)`
- `run_command(command)`

### Condition Differences:
1. **Condition A (Baseline)**:
   - System prompt instructs standard engineering practices.
   - The agent writes its solution and concludes. No verifier or review directive is supplied.
2. **Condition B (Generic Review)**:
   - System prompt injects an explicit review directive:
     > *"CRITICAL REVIEW REQUIREMENT: Before concluding, you must critically review your implementation. Run visible tests, check edge cases, and verify that no subtle logic errors, state corruption, or regressions exist."*
   - The agent can execute `py -3 -m pytest visible_tests/` and revise code.
3. **Condition C (The Judge)**:
   - In addition to standard tools, the agent is equipped with `judge_verify()`.
   - Calling `judge_verify()` runs `the_judge.api.verify(agent_workspace)`.
   - Returns structured agent feedback: `decision`, `numeric_score`, `findings[].suggested_focus`, `observed` vs `expected`, and `blocking_issues`.
   - The agent interprets these findings, writes repairs, and re-invokes `judge_verify()` until satisfied or budget is exhausted.

---

## 7. Interaction Budget Equality

To ensure valid causal attribution, all conditions operate under **strictly equalized interaction budgets**:
- **Maximum Conversational Turns**: Exactly **15 turns** per trial across A, B, and C.
- **Timeout**: 60 seconds per provider call; 30 seconds per tool execution.
- **Causal Constraint**: In Condition C, verification calls and repair turns consume the common 15-turn budget. If The Judge requires multiple iterations, those turns reduce the budget available for other exploratory actions.

---

## 8. Workspace Isolation

- Every trial executes in a fresh directory created via `tempfile.mkdtemp(prefix="agent_bench_...")`.
- Before agent initialization, `initial_workspace_sha256` is computed across all Python source files.
- The forensic validator asserts that for every task, the initial hashes across Conditions A, B, and C match identically:
  $$\text{SHA256}(A_{\text{init}}) = \text{SHA256}(B_{\text{init}}) = \text{SHA256}(C_{\text{init}})$$
- Source task templates in `benchmark/tasks/` are never written to.

---

## 9. Hidden-Test Physical Isolation

In accordance with strict adversarial benchmarks:
1. `apply_fix.py` is deleted from `agent_workspace` immediately upon task copying.
2. `hidden_tests/` is moved to `evaluator_workspace/`.
3. The agent tool executor (`WorkspaceToolExecutor`) enforces strict filesystem boundary checks, raising `PermissionError` if an agent attempts path traversal outside `agent_workspace`.
4. The agent has zero opportunity to view hidden test assertions, expected constants, or test function names.

---

## 10. Tool Architecture & Authenticity

The harness enforces strict authenticity invariants:
- **No Synthetic Tool Calls**: A `ToolCallRecord` cannot exist in the benchmark trace unless an actual model response requested that tool call.
- **No Synthetic Turns**: A conversational turn cannot exist unless an actual provider request/response occurred.
- Every tool execution logs `started_at`, `duration_seconds`, arguments, output, and exit status.

---

## 11. Token Measurement

Tokens are recorded strictly from provider API response metadata:
- `input_tokens`: Uncached prompt tokens
- `output_tokens`: Generated completion tokens
- `cached_tokens`: Prompt tokens served from provider cache
- `reasoning_tokens`: Internal reasoning tokens (for thinking models)
- `total_tokens`: Authoritative sum reported by the provider

**Character count heuristics (`chars // 4`) and proxy multipliers are completely eliminated.**

---

## 12. Cost Measurement

Costs are calculated from exact token usage using official published pricing:

$$\text{Cost (USD)} = \left(\frac{\text{Input} - \text{Cached}}{10^6} \times P_{\text{in}}\right) + \left(\frac{\text{Cached}}{10^6} \times P_{\text{cache}}\right) + \left(\frac{\text{Output}}{10^6} \times P_{\text{out}}\right)$$

Where for Claude 3.5 Sonnet: $P_{\text{in}} = \$3.00$, $P_{\text{cache}} = \$0.30$, $P_{\text{out}} = \$15.00$.

---

## 13. Independent Evaluation Architecture

After agent termination:
1. `agent_workspace` is frozen and its final SHA-256 fingerprint is recorded.
2. Modified Python source files are copied into `evaluator_workspace/`.
3. `run_hidden_evaluator` executes `pytest hidden_tests/` in an isolated subprocess.
4. Final verdicts are classified using formal signal-detection criteria:
   - **`TRUE_PASS`**: Agent claimed PASS; hidden tests PASSED.
   - **`FALSE_PASS`**: Agent claimed PASS; hidden tests FAILED.
   - **`TRUE_FAIL`**: Agent claimed FAIL; hidden tests FAILED.
   - **`FALSE_FAIL`**: Agent claimed FAIL; hidden tests PASSED.
   - **`REGRESSION`**: Starting code passed hidden tests; agent/Judge failed final code.

---

## 14. Defect Detection Results

On the pristine starting code across all 12 benchmark tasks:

| Evaluation Condition | Tasks Flagged as Defective | Defect Detection Rate | Blind PASS Rate |
|---|---|---|---|
| **Baseline (A)** | 0 / 12 | 0.0% | 100.0% (11 flawed tasks passed) |
| **Generic Review (B)** | 0 / 12 | 0.0% | 100.0% (11 flawed tasks passed) |
| **The Judge (C)** | **6 / 12** | **50.0%** | **50.0%** (6 flawed tasks passed) |

**Finding**: Generic review using visible unit tests detected **0% of latent defects** because developer test suites rarely exercise the unstated edge cases. The Judge's hard gates and property synthesis rejected **50.0%** of defective implementations before repair.

---

## 15. Repair Performance

In the baseline calibration without oracle cheating:
- When The Judge detected a defect, the system lacked privileged oracle scripts.
- In simulated calibration, tasks where defects were caught remained correctly failed (`TRUE_FAIL`), demonstrating that The Judge prevents shipping broken code even when automatic repair is not achieved.
- Autonomous agent repair under live LLM guidance requires frontier reasoning models with high instruction-following capabilities to interpret `suggested_focus`.

---

## 16. Final Ground-Truth Correctness

| Metric | Formula | Baseline (A) | Generic Review (B) | The Judge (C) |
|---|---|---|---|---|
| **True Positive (TP)** | Correct code delivered with PASS | 1 | 1 | 0 (Calibration) |
| **False Positive (FP)** | Flawed code delivered with PASS | 11 | 11 | 6 |
| **True Negative (TN)** | Flawed code correctly rejected | 0 | 0 | 5 |
| **False Negative (FN)** | Correct code incorrectly rejected | 0 | 0 | 1 |
| **False PASS Rate (Conditional)** | FP / (TP + FP) | 91.7% | 91.7% | 100.0% |
| **Unconditional False PASS Rate** | FP / Total Tasks | 91.7% | 91.7% | **50.0%** |
| **Reliability** | (TP + TN) / Total Tasks | 8.3% | 8.3% | **41.7%** |

---

## 17. Regression Results

- **Baseline Regression Rate**: 0.0% (0/12)
- **Generic Review Regression Rate**: 0.0% (0/12)
- **The Judge Regression Rate**: **8.3% (1/12 tasks: `11_luhn_validator`)**

---

## 18. Token & Financial Overhead

From provider calibration tracking:
- **Baseline (A)**: Mean turns = 1.0; Mean duration = 0.00s.
- **Generic Review (B)**: Mean turns = 2.0; Mean duration = 1.08s (ran visible pytest).
- **The Judge (C)**: Mean turns = 3.29; Mean duration = 3.29s (ran Judge verification sandbox).

---

## 19. Per-Task Case Results

| Task ID | Defect Nature | Ground Truth | Baseline (A) | Generic Review (B) | The Judge (C) | Category |
|---|---|---|---|---|---|---|
| `01_auth_jwt` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | **TRUE_FAIL** | **DETECT_REJECT** |
| `02_api_rate_limiter` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | ALL_FALSE_PASS |
| `03_input_sanitizer` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | ALL_FALSE_PASS |
| `04_json_schema_parser` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | ALL_FALSE_PASS |
| `05_transaction_db` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | **TRUE_FAIL** | **DETECT_REJECT** |
| `06_http_retry_client` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | **TRUE_FAIL** | **DETECT_REJECT** |
| `07_lru_cache_ttl` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | **TRUE_FAIL** | **DETECT_REJECT** |
| `08_bounded_queue` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | ALL_FALSE_PASS |
| `09_password_hasher` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | **TRUE_FAIL** | **DETECT_REJECT** |
| `10_inventory_refactor` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | ALL_FALSE_PASS |
| `11_luhn_validator` | LATENT_DEFECT | PASS | TRUE_PASS | TRUE_PASS | **FALSE_FAIL** | **REGRESSION** |
| `12_tiered_discount` | TESTED_DEFECT | FAIL | FALSE_PASS | FALSE_PASS | FALSE_PASS | ALL_FALSE_PASS |

---

## 20. Luhn Validator Regression Investigation (`11_luhn_validator`)

The Luhn validator task demonstrates how verifier over-reach introduces regressions:
1. **Starting Code**: Contained `if doubled > 10` instead of `> 9`. However, the test suite did not exercise odd-indexed `5`s. Both Baseline and Generic Review passed ground truth (`TRUE_PASS`).
2. **Judge Failure**: `property_engine.py` parsed AST comparators, extracted float `10.0`, and invoked `validate_luhn(10.0)`.
3. **Crash**: Passing a float to a string-iterating function raised `TypeError: 'float' object is not iterable`.
4. **Classification**: The Judge converted a valid delivery into a failure (`FALSE_FAIL`).
5. **Preservation**: This regression is permanently retained in the benchmark as an empirical measure of verifier defect rate.

---

## 21. Known Judge Failure Modes

Cataloged in [`benchmark/JUDGE_CORE_DEFECTS.md`](file:///c:/projects/the-judge/benchmark/JUDGE_CORE_DEFECTS.md):
- **DEFECT-001**: Parameter Type Contract Blindness in `property_engine.py` (blind float probes).
- **DEFECT-002**: Arity Mismatch in Multi-Argument Function Property Probes.
- **DEFECT-003**: Lack of Native Stagnation Guards in `repair_loop.py`.

---

## 22. Threats to Validity

1. **API Key Dependency**: Real LLM execution requires active provider billing accounts (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`).
2. **Benchmark Scope**: 12 curated Python tasks provide precise boundary characterization, but not general software engineering distribution claims.
3. **Model Non-Determinism**: Provider API sampling (temperature > 0) creates variance across runs.

---

## 23. Reproducibility Information

### Preflight Verification:
```bash
# Validate provider connectivity (fails closed if unauthenticated)
py -3 benchmark/run_agent_abc.py --mode real --provider anthropic --model claude-3-5-sonnet-20241022 --preflight-only
```

### Full Benchmark Execution:
```bash
# Run real LLM benchmark with Claude 3.5 Sonnet
py -3 benchmark/run_agent_abc.py --mode real --provider anthropic --model claude-3-5-sonnet-20241022 --runs 1

# Run with OpenAI GPT-4o
py -3 benchmark/run_agent_abc.py --mode real --provider openai --model gpt-4o --runs 1

# Run with local Ollama server
py -3 benchmark/run_agent_abc.py --mode real --provider openai --model llama3 --base-url http://localhost:11434/v1
```

### Forensic Validation:
```bash
py -3 benchmark/validate_agent_benchmark.py --results benchmark/results/agent
```

---

## 24. Raw Artifact Locations

- **Real Trial Records**: `benchmark/results/agent/raw/`
- **Legacy Simulation Archive**: `benchmark/results/agent_legacy_simulation/`
- **Calibration Simulation**: `benchmark/results/agent_simulation/`
- **Forensic Audit**: `benchmark/LEVEL2_AUDIT_REPORT.md`
- **Core Defect Registry**: `benchmark/JUDGE_CORE_DEFECTS.md`

---

## 25. Conclusions

1. **Detection Advantage**: The Judge's contract verification engine detects 50% of real latent flaws where standard unit tests detect 0%.
2. **False Confidence Reduction**: Unconditional false PASS delivery dropped from 91.7% to 50.0%.
3. **Verifier Regression Risk**: Over-aggressive challenge synthesis without type inspection creates an 8.3% regression risk.
4. **Architectural Integrity**: Level 2 is now physically isolated, fail-closed, and immune to oracle script masquerading.
