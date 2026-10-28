# Regression audit corpus

A labelled corpus for measuring whether `judge verify` discriminates correct from
incorrect code **beyond what the visible tests already show**.

```
python tests/regression_audit/run_audit.py              # judge from this checkout
python tests/regression_audit/run_audit.py --no-tools   # PATH without mypy/ruff
python tests/regression_audit/run_audit.py --judge-src <worktree-of-old-commit>
```

## Layout

```
tasks/<NN_name>/
  task.json            description, module, and one entry per variant:
                       {"variant", "expected": "correct"|"wrong", "bug"}
  visible/test_*.py    weak visible tests, copied to the root of every workspace
  hidden/*.py          ground-truth tests; NEVER copied into the judged workspace
  variants/<name>/     implementation module(s); may override a visible test file;
    baseline/          optional: files committed at git HEAD before the variant's
                       working-tree changes (used for the tampered-test variants)
```

| Task | What the hidden test checks | Wrong variants |
|---|---|---|
| 01_input_validation | `validate_age` type/range rules | accepts bool, rejects 150, accepts float |
| 02_parsing | `parse_duration` grammar | duplicate units, bare number, trailing garbage |
| 03_path_traversal | `safe_join` containment | prefix-only check, `startswith` sibling escape, absolute path |
| 04_nested_transactions | nested begin/commit/rollback | rollback-all, commit flattens, delete not undone |
| 05_concurrency_once | factory runs once under 8 threads | no lock, lock around lookup only |
| 06_decimal_rounding | ROUND_HALF_UP cents, pct range | float math, banker's rounding, no range check |
| 07_hardcoded_lookup | Roman numerals 1..3999 | lookup table for visible inputs, missing XL/XC/CD/CM |
| 08_merge_intervals | sorting, touching intervals | touching not merged, unsorted input |
| 09_ttl_lru_cache | LRU eviction + TTL (2 required ctor args) | unbounded, never expires, FIFO eviction |
| 10_ttl_cache_renamed | same as 09 with renamed identifiers | never expires, unbounded |
| 11_tampered_tests | `dedupe` order | buggy impl + deleted assertion / skip marker / tautology |

## How a variant is scored

1. **Truth**: the variant's implementation is run against `hidden/` in a scratch
   directory. The runner warns if truth disagrees with `task.json`.
2. **Visible**: the implementation is run against the visible tests, so we know
   which bugs the visible tests already catch.
3. **Judge**: a workspace (named `project`, so the variant name does not leak) is
   built from the implementation and visible tests, and `judge verify --json` is
   run on it. Variants with `baseline/` are judged twice: inside a git repo whose
   HEAD holds the honest tests, and as a plain directory (`[no-git]`).

## Metrics

* **False FAIL rate**: correct code judged FAIL. Target 0.
* **False PASS rate**: incorrect code judged PASS.
* **ABSTAIN rate on correct code**.
* **Added value**: bugs that pass the visible tests AND receive a verdict that
  differs from the verdict on the same task's correct implementation. This is the
  number that measures what the judge adds over simply running the visible tests;
  a FAIL that also hits the correct implementation does not count.

`results/` holds the recorded outputs for the original code (commit `9bdff94`) and
for the fixed code, with and without mypy/ruff on PATH.
