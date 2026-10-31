# Simple cache: the verify-repair loop in five commands

A walk-through of the loop from [AGENTS.md](../../AGENTS.md) on a tiny TTL cache.

```
simple_cache/
├── SPEC.md                      # the task: rules R1..R5
├── test_cache.py                # tests written from SPEC.md; each names its rule (# R4)
├── cache.py                     # not implemented yet
└── solutions/
    ├── cache_off_by_one.py      # expires at exactly ttl (violates R4)
    └── cache_correct.py
```

Work on a copy so the example stays as it is:

```bash
cp -r examples/simple_cache /tmp/simple_cache && cd /tmp/simple_cache
```

**1. Freeze the tests before implementing.** Frozen tests count as independent evidence
once the implementation changes afterwards; weakening one later is reported as tampering.

```bash
judge freeze .
```

```
Froze 7 test(s) into .judge/frozen.json:
...
Requirements checklist (5 rules from the spec; ...):
  [covered] R1 (SPEC.md): `get(key)` returns the value most recently stored with ...
  ...
  [covered] R4 (SPEC.md): An entry is returned until exactly `ttl_seconds` have passed ...
```

**2. Implement, with a bug.**

```bash
cp solutions/cache_off_by_one.py cache.py
judge verify .            # exit code 1
```

```
DECISION: FAIL
Numeric Trust Score: 40.0 / 100.0

NEXT ACTIONS
------------
  1. [fix_code] AssertionError: assert None == 'v' ...  (test: test_entry_valid_until_exactly_ttl)
  2. [re_verify] After the fix, verify again.
```

**3. Fix the implementation, not the test.**

```bash
cp solutions/cache_correct.py cache.py
judge verify .            # exit code 0
```

```
DECISION: PASS
Numeric Trust Score: 94.0 / 100.0

NEXT ACTIONS
------------
  1. [done] PASS: all tests passed, including 7 independent test(s) fixed before the
     implementation. The tests caught 5 of 5 planted bugs ...
```

Before PASS the judge planted small bugs in `cache.py` (`>` -> `>=`, a removed `del`, ...)
and checked that some test fails on each. Delete `test_entry_valid_until_exactly_ttl`
and verify again to see what happens when a test is weakened.

**4. Let an agent do steps 2-3.** Reset `cache.py` (`git checkout cache.py` or copy the
stub back), then:

```bash
judge improve .                                   # read-only review: verdict + next actions
judge improve . --agent "claude -p --permission-mode acceptEdits"
```

With `--agent`, each round the agent gets the judge's next actions as its prompt, and the
judge verifies independently after the agent finishes, until PASS or `--max-rounds`.
