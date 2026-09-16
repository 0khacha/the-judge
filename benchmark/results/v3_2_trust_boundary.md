# Comprehensive Forensic Analysis of The Judge Trust Boundary (v3.2)

**Project**: The Judge — Evidence-Gated Quality Layer for AI Coding Agents  
**Date**: September 15, 2026  
**Document**: Architectural Forensic Model of Trust Transitions  

---

## 1. Complete End-to-End Execution Trace

```text
AI-Generated Target Code (impl.py, conftest.py)
      ↓ [Trust Transition 1: Target Workspace Inspection]
Workspace Directory
      ↓ [Trust Transition 2: AST Analysis & Property Inference]
StructurePropertyEngine (judge/property_engine.py)
      ↓ [Trust Transition 3: Challenge Synthesis]
TestSynthesizer (judge/test_synthesizer.py)
      ↓ [Trust Transition 4: Manifest & Pre-Execution Hashing]
Challenge Manifest (expected_challenges JSON) + SHA-256 Hash Guard
      ↓ [Trust Transition 5: Anonymous Sandbox Provisioning]
SandboxRunner (judge/sandbox.py)
      ↓ [Trust Transition 6: Process Creation & Environment Sanitization]
Isolated Python Subprocess (`py -3 -m pytest ...`)
      ↓ [Trust Transition 7: Pytest Collection & Execution]
Pytest Runner + Target Importer
      ↓ [Trust Transition 8: Observation Collection]
Pytest Output Parser (stdout, stderr, exit code)
      ↓ [Trust Transition 9: Post-Execution Integrity Verification]
Post-Execution SHA-256 Hash & Manifest Validation
      ↓ [Trust Transition 10: Evidence Graph Integration]
ScoreEngine (judge/score_engine.py)
      ↓ [Trust Transition 11: Final Verdict Generation]
PASS / FAIL / ABSTAIN Verdict
```

---

## 2. Forensic Component Analysis Matrix

| Execution Stage / Component | Input Control | Filesystem Control | Process Control | Import Control | Timing Control | Evidence Control | Persistence Between Runs | Vulnerability / Assumption |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Target Code (`impl.py`)** | Target | Target Workspace | None (Static) | Target Workspace | None | Agent Claim | Workspace files | Target code is untrusted and actively adversarial. |
| **2. Target Config (`conftest.py`)** | Target | Target Workspace | Subprocess Hooks | Python Sys Path | Hook Execution | Test Outcomes | Workspace files | Target can define pytest hooks (`pytest_collection_modifyitems`, `pytest_runtest_protocol`). |
| **3. Property Engine (`property_engine.py`)** | Judge | Temp Sandbox | Judge Controller | Trusted | Judge | AST Candidates | Memory | **Assumption**: AST parser sees true target logic. **Risk**: Obfuscated AST misleads inference. |
| **4. Challenge Manifest** | Judge | Temp Sandbox | Judge Controller | Trusted | Judge | Manifest JSON | Temp Dir | **Assumption**: Manifest freeze protects test identity. **Risk**: Pre-manifest target structure dictates manifest items. |
| **5. Sandbox Provisioning (`sandbox.py`)** | Judge | Temp Dir | Subprocess | Isolated Env | Judge | Subprocess Payload | Isolated Temp Dir | **Assumption**: Temporary directory isolates files. **Risk**: System `/tmp` or shared OS handles allow cross-process leaks. |
| **6. Subprocess Creation** | Judge | Temp Dir | OS Kernel | Python Sys Path | OS Scheduler | Exit Code, Stdout | Process Table | **Assumption**: Child process dies cleanly. **Risk**: Background daemon threads or spawned processes persist. |
| **7. Pytest Execution** | Target + Judge | Temp Dir | Subprocess | `sitecustomize` / `sys.path` | Execution | Pytest Reports | In-Memory `sys.modules` | **Assumption**: Pytest runs challenge tests. **Risk**: Target import hooks or `.pth` files hijack pytest execution. |
| **8. Post-Execution Hashing** | Judge | Temp Dir | Judge Controller | Trusted | Judge | SHA-256 Hashes | Temp Dir | **Assumption**: Single post-execution check catches changes. **Risk**: TOCTOU race window between hash and process exit. |
| **9. Evidence Graph & Score Engine** | Judge | Controller | Judge Controller | Trusted | Judge | Final Verdict | Report JSON | **Assumption**: Hard Gates catch all anomalies. **Risk**: ABSTAIN manipulation (denial of verification). |

---

## 3. Targeted Forensic Questions & Hard Answers

### 1. Who controls the input?
- **Public Tests**: Target controls workspace tests.
- **Synthesized Probes**: Judge controls inputs (`ValueGenerator` with fixed seeds and boundary sets).
- **Vulnerability**: If target recognizes probe input distributions (e.g. `100.0`, `0`, `""`), it can selectively behave correctly during probes.

### 2. Who controls the filesystem?
- **Workspace**: Target has write access to target workspace.
- **Sandbox**: Sandbox is created in temporary directory. However, target code running inside the sandbox process has full write access to its current working directory and system temp directory (`C:\Temp` or `/tmp`).
- **Vulnerability**: Target can create symlinks, hard links, or drop `.pth` / `sitecustomize.py` files in working directory before pytest starts.

### 3. Who controls the process?
- **Parent Controller**: Trusted Judge running Python process.
- **Child Execution**: Subprocess running pytest.
- **Vulnerability**: Target running inside child process can spawn background subprocesses (`subprocess.Popen`), create detached daemons, or modify process environment variables inherited by child subprocesses.

### 4. Who controls imports?
- **Python Import System**: Default `sys.meta_path`, `sys.path`, `site-packages`, and working directory.
- **Vulnerability**: Target code executed during `conftest.py` loading or module import can mutate `sys.meta_path`, `sys.modules`, or `builtins.__import__`, altering how synthesized challenge tests load modules.

### 5. Who controls test execution?
- **Pytest Protocol**: Pytest runner executes test items collected by `pytest_collectfile`.
- **Vulnerability**: Pytest hooks (`pytest_runtest_protocol`, `pytest_runtest_makereport`) executed inside the subprocess are target-controllable if defined in target `conftest.py`.

### 6. Who controls timing?
- **System Clock**: Target code can read `time.time()` or `time.monotonic()`.
- **Vulnerability**: Target can delay execution (sleep) or detect fast probe execution intervals to differentiate probes from test sessions.

### 7. Who controls evidence?
- **Raw Observations**: Derived from subprocess stdout/stderr and exit code.
- **Verified Evidence**: Judge cross-checks passed tests against Expected Challenge Manifest and SHA-256 file hashes.
- **Vulnerability**: If target forces an unhandled exception or module import crash, pytest exits with non-zero status or fails collection. If Judge treats this as ABSTAIN, target successfully denies verification on a broken implementation.

### 8. What can persist between processes?
- OS system temporary directories (`C:\Temp` or `/tmp`).
- Environment variables modified at user/system level.
- Background processes spawned via `subprocess.Popen(..., creationflags=DETACHED_PROCESS)`.

### 9. What can be modified between verification stages?
- The challenge file `_synthesized_property_tests.py` on disk between pre-hashing and Python import.
- `sys.modules` cache when imports are executed in sequence within the same process.

### 10. What assumptions does the Judge make?
1. *Assumption*: Hashing a challenge file before and after execution detects tampering. (Vulnerable to TOCTOU window *during* execution).
2. *Assumption*: Subprocesses running in temporary directories cannot affect parent or sibling subprocesses. (Vulnerable to shared filesystem or OS IPC handles).
3. *Assumption*: If challenge synthesis generates 0 challenges due to AST structure ambiguity, ABSTAIN is safe. (Vulnerable to deliberate ABSTAIN manipulation).

### 11. Which observations are genuinely independent?
- Fresh-process state-reset probes (`out_fresh` from a separate subprocess) ARE independent of in-process state.
- SHA-256 hash of challenge code created by trusted Judge IS independent of target claim.
- Pytest stdout text IS NOT independent of target code if target overrides stdout or pytest hooks.

---

## 4. Trust Transition Risk Mapping

```text
Trust Transition 1: Target Workspace Inspection -> UNTRUSTED
Trust Transition 2: AST Analysis & Property Inference -> DEPENDENT ON AST INTEGRITY
Trust Transition 3: Challenge Synthesis -> TRUSTED ENGINE
Trust Transition 4: Manifest & Pre-Execution Hashing -> TRUSTED BOUNDARY
Trust Transition 5: Anonymous Sandbox Provisioning -> ISOLATED
Trust Transition 6: Process Creation & Env Sanitization -> ISOLATED
Trust Transition 7: Pytest Collection & Execution -> UNTRUSTED IN-PROCESS EXECUTION
Trust Transition 8: Observation Collection -> UNTRUSTED OUTPUT STREAM
Trust Transition 9: Post-Execution Integrity Verification -> TRUSTED CHECK
Trust Transition 10: Score Engine Evaluation -> TRUSTED HARD GATES
```

*Conclusion*: The primary remaining attack vectors reside in **Trust Transition 7 (In-Process Pytest Execution)**, **TOCTOU Filesystem Races in Sandbox Provisioning**, and **Synthesis Ambiguity (ABSTAIN Manipulation)**.
