# The Judge v4.0 Threat Model

## Overview

The threat model of The Judge v4.0 evaluates possible attack vectors an untrusted target implementation (or AI coding agent) might attempt to bypass verification, obscure behavioral failures, manipulate evidence, or trigger false PASS decisions.

---

## Threat Actors & Capabilities

### Adversarial Agent / Untrusted Target Code
- **Capability 1**: Inspect local workspace files, inspect process stack traces, check `sys.argv`, and inspect environment variables.
- **Capability 2**: Override standard Python library behavior, intercept module imports, patch inspect/sys builtins.
- **Capability 3**: Selectively fail or pass based on detection of verifier execution context.
- **Capability 4**: Modify or delete test files during pytest discovery/collection.
- **Capability 5**: Return dummy fallback values or raise synthetic exceptions to force `ABSTAIN`.

---

## Attack Surface & Mitigations

| Threat Vector | Attack Description | Verifier Defense / Mitigation | Status |
|---|---|---|---|
| **Identifier Detection** | Target inspects `sys.argv` or stack frames to detect test runner names (e.g. `_synthesized_tests`). | `SandboxRunner` runs with sanitized `sys.argv` and anonymous temporary files. | **VERIFIED** |
| **Test Collection Manipulation** | Target modifies pytest test collection or monkeypatches `pytest_collect_file`. | `Hard Gate 7 (Challenge Tampering)` verifies SHA-256 hashes & expected test manifest. | **VERIFIED** |
| **Call Counter Fake Uniqueness** | Target uses internal call counters to simulate randomness without actual entropy. | `PropertyEngine` executes fresh subprocess state checks to detect call-counter state. | **VERIFIED** |
| **Synthesis Evasion** | Target writes implementation that satisfies visible tests but fails hidden properties. | `Synthesis Evasion Policy` forces `ABSTAIN` if 0 independent challenge tests pass. | **VERIFIED** |
| **Verification Denial** | Target deliberately crashes pytest or raises `SystemExit` to force `ABSTAIN`. | `Hard Gate 8 (Verification Denial)` detects forced abstention attempts and returns `FAIL`. | **VERIFIED** |
| **Multi-Round Silent Regression** | Target fixes feature B in Round 2 while silently breaking feature A. | `Hard Gate 6 (Multi-Round Regression Protection)` compares evidence snapshots across rounds. | **VERIFIED** |

---

## Non-Goals & Out-of-Scope Limitations

The Judge is **NOT**:
1. A formal proof system or mathematical verifier.
2. A guarantee of zero software bugs in all possible state spaces.
3. Proof that arbitrary unstated specifications are satisfied.

It is:
> **An evidence-based behavioral verification layer that independently verifies observable software contracts and property invariants under an untrusted execution model.**
