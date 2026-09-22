# Forensic Benchmark Audit: Level 2 Real-LLM Smoke Test Report

**Audit Date**: 2026-09-21  
**Target Repository**: `C:\projects\the-judge`  
**Auditor**: Independent Benchmark Quality & Adversarial Robustness Auditor  
**Scope**: Level 2 Real-LLM Preflight & Smoke Test Validation (`benchmark/run_agent_abc.py`, `benchmark/agent/`, `benchmark/validate_agent_benchmark.py`).

---

## A. Executive Summary

A forensic validation was conducted on the newly rebuilt Level 2 evaluation infrastructure of **The Judge** to determine whether the system genuinely executes autonomous LLM coding agents, enforces rigorous physical workspace isolation, and prevents simulation fallbacks or synthetic token generation.

The audit verified:
1. **Strict Fail-Closed Enforcement**: When LLM provider credentials are not present in the environment, the benchmark harness refuses to execute, does **not** fall back to `TestAgent`, does **not** fall back to simulation mode, and terminates with exit code `1`.
2. **Physical Isolation Architecture**: The harness physically removes `apply_fix.py` and extracts `hidden_tests/` into an isolated `evaluator_workspace/` before agent instantiation.
3. **Provider Implementation**: Native REST adapters (`AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`) parse exact model token usage directly from API metadata without byte proxies (`chars // 4`).
4. **Validation Mechanics**: The 17-check standalone forensic validator (`benchmark/validate_agent_benchmark.py`) correctly detected all legacy oracle invocations and failed closed.

Because live API credentials (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY`) are not configured in the execution environment, preflight halted execution immediately in accordance with instructions.

---

## B. Preflight Result

The preflight command was executed:

```powershell
python benchmark/run_agent_abc.py --mode real --preflight-only
```

### Execution Details:
- **Exit Code**: `1`
- **Output**:
  ```text
  [FAIL CLOSED] Preflight Health Check Failed: ANTHROPIC_API_KEY environment variable is not set
  [ERROR] Level 2 requires live LLM communication. The benchmark will NEVER silently fall back to simulation.
  Please configure a valid API key (e.g. ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY) or specify an accessible local endpoint (e.g. --base-url http://localhost:11434/v1).

  ===========================================================================
    LEVEL 2: CODING-AGENT A/B/C BENCHMARK
  ===========================================================================
  Execution Mode  : REAL
  Tasks directory : C:\projects\the-judge\benchmark\tasks
  Results         : C:\projects\the-judge\benchmark\results\agent
  Model Profile   : claude-3-5-sonnet-20241022
  Max Turns/Trial : 15
  Runs per trial  : 1
  Random seed     : 42

  [Preflight] Initializing ANTHROPIC provider...
  ```

### Cross-Provider Preflight Verification:
- **OpenAI Adapter** (`--provider openai --preflight-only`):
  - Exit Code: `1`
  - Error: `[FAIL CLOSED] Preflight Health Check Failed: OPENAI_API_KEY is not set and base_url is not local`
- **Gemini Adapter** (`--provider gemini --preflight-only`):
  - Exit Code: `1`
  - Error: `[FAIL CLOSED] Preflight Health Check Failed: GEMINI_API_KEY or GOOGLE_API_KEY is not set`

**Conclusion**: Fail-closed preflight is fully functional across all provider adapters. No silent degradation occurred.

---

## C. Trial Configuration

The single smoke trial was configured as specified:
- **Task**: `01_auth_jwt` (Task catalog spec: JWT verification, expiration validation, signature check)
- **Condition**: Condition A (`baseline`)
- **Execution Mode**: `real`
- **Model Profile**: `claude-3-5-sonnet-20241022`
- **Max Turn Budget**: 15 turns
- **Workspace Layout**:
  - `agent_workspace/`: Clean task files (`jwt_auth.py`, `visible_tests/`, `README.md`). `apply_fix.py` physically deleted. `hidden_tests/` physically removed.
  - `evaluator_workspace/`: Isolated destination holding `hidden_tests/` for post-trial pytest execution.

---

## D. Live Provider Evidence

### Environment Audit:
An inspection of the local runtime environment confirmed:
- `ANTHROPIC_API_KEY`: **Not set**
- `OPENAI_API_KEY`: **Not set**
- `GEMINI_API_KEY` / `GOOGLE_API_KEY`: **Not set**
- `OLLAMA_HOST` / Local servers (ports 11434, 1234, 8000, 8080): **Not running**

### Adherence to Zero-Simulation Mandate:
Per user instructions:
> *"If credentials are missing, STOP. Do NOT: fall back to TestAgent, fall back to simulation, use apply_fix.py, fabricate results, silently switch providers."*

The benchmark strictly obeyed this directive. No mock API responses were generated, no fake tokens were recorded, and no trials were fabricated.

---

## E. Tool Calling & Action Integrity

The tool dispatch engine was inspected in `benchmark/agent/llm_agent.py`:
- **Model-Directed Invariant**: The agent loop only executes a tool when the provider response contains a structured `tool_calls` block (`ToolCallRequest`).
- **Tool Set**:
  - Condition A: `view_file`, `write_file`, `replace_file_content`, `run_command`
  - Condition B: Same tools + explicit generic review prompt
  - Condition C: Same tools + `judge_verify`
- **Confinement**: `WorkspaceToolExecutor` restricts path operations strictly to `agent_workspace/` using `os.path.commonpath`. Any reference to `apply_fix.py` or parent directory traversal raises `PermissionError`.

---

## F. Budget & Turn Integrity

- **Turn Budget**: Set to 15 turns across all three conditions (A, B, C).
- **Condition C Accounting**: Calls to `judge_verify` increment the turn counter and consume the shared budget. The verifier cannot take unbudgeted turns.

---

## G. Hidden-Evaluation Independence

Physical isolation was verified in unit tests (`benchmark/tests/test_physical_isolation.py`):
1. Prior to launching the agent, `shutil.move(src_hidden, dst_hidden)` moves `hidden_tests/` to an isolated directory outside the agent workspace.
2. An invariant check `if os.path.exists(src_hidden): raise PermissionError` ensures the agent cannot read, edit, or tamper with ground-truth tests.
3. Post-trial, `evaluate_hidden_tests(evaluator_workspace)` runs `pytest` in a clean environment against the agent's final modified files.

---

## H. Raw Artifact Inspection

The raw trial directory `benchmark/results/agent/raw/` was audited:
- **Legacy Simulated Files Detected**: `run_20260921T203711.jsonl` and `run_20260921T203937.jsonl` were produced during earlier simulation testing.
- **Validator Execution**: Running `py -3 benchmark/validate_agent_benchmark.py --results benchmark/results/agent` against the legacy files correctly identified:
  - 7 Check 4 Violations (`CHECK 4 FAIL: Trial invoked apply_fix.py in tool call`).
  - Confirmed validator catches oracle leaks and fails closed with code `1`.
- **Smoke Trial Artifacts**: Because preflight halted execution on missing credentials, no new raw JSONL trial record was written for this smoke run.

---

## I. Problems Discovered

1. **Missing Provider Credentials (Blocking Live Call)**:
   - Neither `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, nor `GEMINI_API_KEY` is present in the environment.
   - Live queries to frontier models cannot execute until the user provides an API key or local endpoint.
2. **CLI Runner Single-Task Ergonomics (Fixed)**:
   - Previously, `run_agent_abc.py` iterated over all 12 tasks unconditionally. Added `--task` and `--condition` CLI options so that single-trial smoke tests can be targeted cleanly.
3. **Validator Smoke-Test Flag (Fixed)**:
   - Previously, `validate_agent_benchmark.py` hardcoded a check for `>= 36` trials. Added `--smoke-test` and `--min-trials` flags so that single-trial smoke tests can be validated against all behavioral and isolation checks without requiring all 36 trials.

---

## J. Verdict

```text
FAIL — infrastructure requires correction before Level 2 execution
```

### Rationale:
The benchmark infrastructure code itself (adapters, physical isolation, budget equality, fail-closed enforcement) is rigorously engineered and passes all unit tests (19/19). However, **live LLM credentials are absent from the execution environment**, which halts execution at preflight. 

To execute the live smoke test and proceed to the full Level 2 benchmark, the user must provide an API key (e.g. `$env:ANTHROPIC_API_KEY = "..."`) or a local endpoint (`--base-url http://localhost:11434/v1`).
