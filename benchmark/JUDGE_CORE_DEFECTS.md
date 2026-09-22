# The Judge Core Defects Audit & Registry

**Target Component**: `the_judge/core/property_engine.py` (and associated synthesis modules)  
**Date**: 2026-09-21  
**Integrity Rule**: Per benchmark rules and AGENTS.md, `the_judge/core/` is preserved without ad-hoc patches to ensure benchmark transparency. These defects are formally registered and analyzed here.

---

## Defect 1: Blind Single-Float Invocation of Arbitrary Functions in Boundary Synthesis

### Summary
The boundary property inference engine (`_infer_boundary_candidates` in `the_judge/core/property_engine.py`, lines 63–106) extracts numeric constants from any `ast.Compare` node in a module and generates challenge test cases that invoke every function in that module with a single floating-point argument (`fn({num})`), ignoring function arity, parameter names, and type annotations.

### Minimal Reproduction
```python
# Save as sample_task.py
def validate_luhn(card_number: str) -> bool:
    if len(card_number) > 10:
        return True
    return False

# Run challenge synthesis on sample_task.py
python -c "
import ast
from the_judge.core.property_engine import PropertyInferenceEngine
with open('sample_task.py') as f:
    tree = ast.parse(f.read())
engine = PropertyInferenceEngine()
candidates = engine._infer_boundary_candidates(tree, 'sample_task')
for c in candidates:
    print(c.challenge_code)
"
```
Generated challenge code:
```python
def test_prop_boundary_perturbation_sample_task_validate_luhn_10():
    fn = getattr(sample_task, 'validate_luhn')
    res_exact = fn(10.0)
    res_minus = fn(9.99)
    res_plus = fn(10.01)
    assert res_exact is not None, "Boundary threshold function returned None"
```

### Expected Behavior
1. **Type Awareness**: Functions with type annotations (e.g. `card_number: str` or `payload: bytes`) must not be invoked with `float` literals. If boundary values are extracted, they must be formatted according to the parameter's expected type (e.g. `"10"`, `"0000000000"`).
2. **Arity Awareness**: Functions with multiple required parameters must not be called with only one argument.
3. **Scope Association**: Comparison constants found inside function $A$ should not be applied to function $B$.

### Actual Behavior
- `fn(10.0)` is called directly on `validate_luhn(card_number: str)`.
- Inside `validate_luhn`, `[int(c) for c in card_number if c.isdigit()]` crashes with:
  ```text
  TypeError: 'float' object is not iterable
  ```
- The Judge classifies this unhandled exception as a behavioral failure (`GATE-001` / test suite failure), giving a score of 63.33 and verdict `FAIL`.
- Even when `apply_fix.py` correctly repairs the logic from `doubled > 10` to `doubled > 9`, the test synthesizer re-synthesizes the exact same float invocation, failing valid code on all 5 rounds.

### Impact on Benchmark
- **Benchmark-level regression**: Task `11_luhn_validator` was degraded from `TRUE_PASS` (Baseline and Generic Review) to `FALSE_FAIL` (The Judge).
- **Resource waste**: Incurred 5 rounds of execution and 7.53× token-equivalent overhead on a task that was already correct.

### Proposed Fix
In `the_judge/core/property_engine.py`:
1. Check `fn.args.args`: If `len(args) != 1` (or required positional arguments > 1), skip boundary probe or generate mock default arguments for remaining parameters.
2. Inspect `fn.args.args[0].annotation`:
   - If `ast.Name(id='str')`, format boundary constant as string: `str(int(num))`.
   - If `ast.Name(id='bytes')`, format as bytes: `bytes([int(num) % 256])`.
   - If `ast.Name(id='int')`, format as integer `int(num)`.
   - Only pass `float` if annotation is `float` or unannotated.
3. Only test functions that actually enclose the comparison node, rather than broadcasting module-wide constants across every function.

---

## Defect 2: Multi-Argument Function Invocation in Challenge Probes

### Summary
In `01_auth_jwt`, the function `decode_token` has the signature:
```python
def decode_token(token: str, secret: str, algorithms: list = None) -> dict:
```
The property engine attempts to invoke `decode_token(4.0)` and `decode_token(3.0)` because `jwt_auth.py` contains constants `4` and `3`.

### Minimal Reproduction
```python
# Task: 01_auth_jwt
python -c "
from the_judge.core.evidence import capture_evidence
ev = capture_evidence('benchmark/tasks/01_auth_jwt')
for test, err in ev['test_suite'].get('errors', {}).items():
    print(test, '->', err)
"
```
Observed failures:
```text
TypeError: decode_token() missing 1 required positional argument: 'secret'
TypeError: _b64_encode() argument 1 must be bytes-like object, not float
```

### Expected Behavior
The challenge synthesizer must inspect function signatures before generating call statements. If required parameters cannot be inferred or mocked, synthesis for that function must abstain rather than emitting code guaranteed to crash with `TypeError`.

### Actual Behavior
Emitted invalid Python calls that failed regardless of whether the JWT expiration flaw was fixed or not. In `01_auth_jwt`, this caused 10 blocking issues to recur across all 5 rounds, masking the fact that `apply_fix.py` had actually fixed the expiration defect.

### Impact on Benchmark
- Prevented `01_auth_jwt` from achieving `TRUE_PASS` after repair, resulting in `DETECT_BUT_CANNOT_VERIFY` / `FALSE_FAIL`.
- Created 63.0% evidence duplication across 5 rounds.

### Proposed Fix
Implement parameter signature validation in `PropertyInferenceEngine`:
```python
def _can_synthesize_call(fn: ast.FunctionDef) -> bool:
    required_args = [a for a in fn.args.args if a.arg != 'self']
    # If defaults exist, only count args without defaults
    num_defaults = len(fn.args.defaults)
    num_required = len(required_args) - num_defaults
    return num_required == 1
```

---

## Defect 3: Lack of Loop Stagnation Detection in Repair Engine

### Summary
In `repair_loop.py` (and reproduced in benchmark Condition C), if a verification gate fails and a repair action is taken, the loop does not check whether the workspace content actually changed or whether the evaluation score / blocking findings stagnated.

### Minimal Reproduction
Run Condition C on `11_luhn_validator`, `01_auth_jwt`, or `09_password_hasher`.

### Expected Behavior
If round $N$ produces identical workspace files or identical `(numeric_score, set(blocking_issues))` compared to round $N-1$, the engine should terminate with `STOP_REASON = STAGNATION` instead of running to `max_rounds=5`.

### Actual Behavior
The loop executed 5 rounds, re-running the sandbox and re-executing visible tests 5 times, resulting in 63% to 67% evidence duplication.

### Impact on Benchmark
Artificially inflated Condition C runtime by ~40 seconds and ~30,000 bytes of redundant data across 3 tasks.

### Proposed Fix
Implement semantic stagnation guards checking:
1. Workspace SHA-256 before repair vs. after repair.
2. Normalized blocking issues set between rounds.

---

## Benchmark Handling Strategy

Rather than hiding these defects or modifying `the_judge/core/` to make the numbers look artificially favorable:
1. The deterministic benchmark preserves these findings as empirical evidence of The Judge's current capabilities and boundaries.
2. The benchmark reporting system classifies `11_luhn_validator` explicitly as a `REGRESSION`.
3. Tasks `01_auth_jwt` and `09_password_hasher` are classified as `DETECT_BUT_CANNOT_VERIFY`.
4. Stagnation detection is implemented in the benchmark harness and recommended for inclusion in `the_judge/integrations/repair_loop.py`.
