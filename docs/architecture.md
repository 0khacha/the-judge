# The Judge v4.0 Architecture Specification

## Overview

The Judge v4.0 is structured as an **adversarial, evidence-gated verification layer**. Its primary architecture separates untrusted AI target execution from trusted verification and scoring.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AI CODING AGENT                                 │
│  (Generates or modifies implementation code in untrusted workspace)   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       THE JUDGE PUBLIC API                             │
│                     the_judge.verify(workspace)                        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ BehaviorEngine  │       │ PropertyEngine  │       │  SandboxRunner  │
│ Black-box probes│       │ AST Inference   │       │ Isolated Subproc│
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      GROUND TRUTH EVIDENCE                             │
│                  capture_evidence(workspace_dir)                       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      SCORE & TRUST PROFILE ENGINE                      │
│                                                                        │
│   Hard Gates 1–8:                                                      │
│   - Gate 1: Test Suite Failures                                        │
│   - Gate 2: Type Checker Errors                                        │
│   - Gate 3: Blocking Security Notes                                   │
│   - Gate 4: Requirement Failures                                       │
│   - Gate 5: Discrepancy Gate (Claim vs Ground Truth)                   │
│   - Gate 6: Multi-Round Regression Protection                          │
│   - Gate 7: Test Collection & Challenge Tampering Gate                 │
│   - Gate 8: Verification Denial / ABSTAIN Manipulation Gate            │
│                                                                        │
│   5-Dimension Trust Profile Engine:                                   │
│   1. Environment Isolation (Process, FS, Env, Import, Cross-run)       │
│   2. Evidence Integrity (Challenge, Collection, Execution, Result)    │
│   3. Behavioral Coverage (Boundary, Perturbation, State, Semantic)     │
│   4. Adversarial Robustness (Known, Adaptive, Temporal, Evasion)       │
│   5. Abstention Correctness (Insufficient, Conflicting, Denial)        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      VERIFICATION RESULT                               │
│                   PASS  │  FAIL  │  ABSTAIN                            │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AGENT ADAPTER LAYER                             │
│            Formats structured findings (no hidden source code)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Directory & Package Structure

```text
the_judge/
├── core/
│   ├── sandbox.py             # Anonymous subprocess sandbox execution environment
│   ├── behavior_engine.py     # Stateful black-box behavioral probe generator
│   ├── property_engine.py     # Structure-driven AST behavioral property inference
│   ├── evidence.py            # Subprocess evidence capture & manifest tracking
│   ├── score_engine.py        # Deterministic score engine & Hard Gates 1-8
│   └── decision.py            # VerificationResult & Finding dataclass models
│
├── integrations/
│   ├── agent_adapter.py       # Actionable feedback transformer for AI agents
│   ├── repair_loop.py         # Multi-round repair orchestrator & regression tracker
│   ├── cli.py                 # Terminal human-readable & JSON interface
│   └── demo.py                # 60-second interactive demonstration mode
│
├── schemas/
│   ├── task.schema.json       # Task specification contract schema
│   ├── result.schema.json     # VerificationResult JSON schema
│   └── evidence.schema.json   # Ground truth evidence schema
│
└── api.py                     # Public entrypoints: verify() and verify_workspace()
```

---

## Hard Gates 1–8 Specification

1. **Gate 1 (Test Suite Failure)**: Triggers `FAIL` if any executable test fails or process returns non-zero exit code.
2. **Gate 2 (Type Checker)**: Triggers `FAIL` if type checking fails with unhandled type errors.
3. **Gate 3 (Blocking Security)**: Triggers `FAIL` if security analysis reveals blocking vulnerabilities.
4. **Gate 4 (Requirement Failure)**: Triggers `FAIL` if explicit task spec requirements evaluate to fail status.
5. **Gate 5 (Discrepancy Check)**: Triggers `FAIL` if agent claims `PASS` on a requirement that failed in ground truth execution.
6. **Gate 6 (Multi-Round Regression Protection)**: Triggers `FAIL` if a previously passing test in Round *N-1* fails in Round *N*.
7. **Gate 7 (Challenge Tampering & Collection Gate)**: Triggers `FAIL` if target code modifies challenge test files or evades test collection.
8. **Gate 8 (Verification Denial Gate)**: Triggers `FAIL` if target code attempts to obscure execution or force invalid `ABSTAIN`.

---

## Trust Boundary Invariants

- **Untrusted Workspace**: Target code and test files written by the AI agent are treated as strictly untrusted.
- **Anonymous Execution**: Challenge tests run in randomly named temporary files in isolated sandboxes to prevent test name detection.
- **Environment Sanitization**: Target subprocesses run with sanitized `sys.argv`, cleared debug environment variables, and isolated import paths.
