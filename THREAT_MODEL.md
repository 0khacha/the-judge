# The Judge v4.0 Threat Model

## Overview

The threat model of The Judge v1.0 evaluates possible attack vectors an untrusted target implementation (or AI coding agent) might attempt to bypass verification, obscure behavioral failures, manipulate evidence, or trigger false PASS decisions.

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
| **Test Collection Manipulation** | Target modifies pytest test collection or monkeypatches `pytest_collect_file`, or uses a conftest.py hook to silently drop specific tests. | `Hard Gate 7 (Challenge Tampering)` verifies SHA-256 hashes & expected test manifest. Manifest now includes both synthesized probe tests **and** statically-discovered test functions from visible `test_*.py` files, so collection tampering is detected in both contract mode and no-contract (ad-hoc) mode. | **VERIFIED** |
| **Call Counter Fake Uniqueness** | Target uses internal call counters to simulate randomness without actual entropy. | `PropertyEngine` executes fresh subprocess state checks to detect call-counter state. | **VERIFIED** |
| **Synthesis Evasion** | Target writes implementation that satisfies visible tests but fails hidden properties. | `Synthesis Evasion Policy` forces `ABSTAIN` if 0 independent challenge tests pass. | **VERIFIED** |
| **Crash-to-PASS (Swallowed Exceptions)** | Target code raises on every input; auto-generated probes previously swallowed the exception and recorded no failure, producing a false PASS. | `BehaviorEngine` and `PropertyEngine` probes now only catch `TypeError` (probe not applicable due to arity/type mismatch); all other exceptions propagate as test failures. | **VERIFIED** |
| **Trivial Requirement Coverage** | A critical requirement is falsely marked VERIFIED by a trivially-passing existence test that only asserts the module exports a symbol. | Trivial existence tests are no longer generated for contract requirements. Requirements with no structural AST evidence remain `UNVERIFIED`, triggering Hard Gate 9 → `ABSTAIN`. | **VERIFIED** |
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

### Current scope of auto-generated probes

Auto-generated ("vocabulary-free") probes detect idempotency violations, state-isolation failures, boundary perturbation, expiration, capacity, uniqueness, and always-crashing code. They do **not** catch:

- Semantic errors in numeric functions (e.g. `add(a, b)` returning `0` — wrong value, right type).
- Multi-argument business logic that requires coordinated inputs to exercise.

See the [Known Limitations of Auto-Generated Probes](README.md#known-limitations-of-auto-generated-probes) section in README.md for the full table.
