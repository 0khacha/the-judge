# Evaluation 2: does the-judge-verify 1.0.1 make an agent's code more correct?

Pre-registered in [`PROTOCOL.md`](PROTOCOL.md) (SHA-256 in `PROTOCOL.sha256`, hashed
2026-10-28T22:56:11 before any task existed). Raw data: [`eval2/`](eval2/).

## Result

**No evidence** (pre-registered decision rule). The judge did not make Claude Haiku's
final code more correct on hidden tests.

| | A (baseline) | B (with judge 1.0.1) |
|---|---|---|
| Runs | 30 | 30 |
| Mean hidden-test pass rate | 99.80% | 99.80% |
| Fully correct final runs | 29 | 29 |
| Mean tokens per run | 39,322 | 48,969 (+25%) |
| Mean wall time per run | 94 s | 263 s (2.8x) |

D = 0.0 percentage points, 95% bootstrap CI [-0.39, +0.39] (10,000 resamples within
task x condition). Rule: clear improvement needs D >= 10 points; marginal needs D >= 3.

**Why:** no headroom. The baseline solved 29 of 30 runs completely. The one failure in
each condition was the same hidden case (T6, run 4: a lone `\r` right after a closing
quote must raise `ValueError`).

## Per task

| Task | A hidden | B hidden | A fully correct | B fully correct | B final PASS | B verify calls (mean) | A tokens | B tokens | A s | B s |
|---|---|---|---|---|---|---|---|---|---|---|
| T1_semver | 100.0% | 100.0% | 5/5 | 5/5 | 5/5 | 2.0 | 38096 | 46792 | 77 | 282 |
| T2_money | 100.0% | 100.0% | 5/5 | 5/5 | 5/5 | 1.4 | 37916 | 46196 | 73 | 261 |
| T3_exprlib | 100.0% | 100.0% | 5/5 | 5/5 | 5/5 | 2.0 | 42346 | 49442 | 151 | 286 |
| T4_orders | 100.0% | 100.0% | 5/5 | 5/5 | 3/5 | 2.0 | 39384 | 51270 | 106 | 282 |
| T5_wrap | 100.0% | 100.0% | 5/5 | 5/5 | 4/5 | 1.6 | 39060 | 49216 | 75 | 271 |
| T6_csv | 98.8% | 98.8% | 4/5 | 4/5 | 5/5 | 1.0 | 39129 | 50899 | 82 | 199 |

Every task except T6 has no headroom (A 100% in all 5 runs). "Verify calls" of 2.0 are
mostly agents re-running a PASS verify to read the (long) JSON again.

## The judge's own behaviour (B runs)

- **Judge false PASS: 1 real.** T6 B r4: PASS on code that fails one hidden test. The
  agent's tests did not cover the case. (The harness also reports 2 false PASSes for
  T3 B r4: that agent ran the wrapper from another directory with an absolute path, so
  the wrapper snapshotted the wrong directory. The judge verified the right one and the
  final code passes all hidden tests. Counted as a harness artifact, not a false PASS.)
- **Judge false FAIL: 0.** Regressions: 0. No frozen test was weakened to obtain PASS.
- **Iterations to PASS:** 27 of 30 runs reached PASS, all at the first verify after
  implementing.
- **Final ABSTAIN with correct code: 3 runs** (T4 r4, T4 r5, T5 r1). Each agent found a
  wrong expectation in its own frozen test after implementing, corrected it and re-froze;
  the rule then counted *all* tests as frozen after the code. Each agent stopped and
  reported ABSTAIN honestly.
- **Actionable ABSTAIN fraction: 0 of 6.** Every ABSTAIN was either the last call or was
  followed by the same ABSTAIN.
- **Judge accuracy (no agent, visible tests frozen first):** reference solutions PASS on
  5 of 6 tasks; both wrong solutions also PASS on those 5 (the visible tests do not test
  what the hidden tests test, and the judge cannot know). On T3 all three got ABSTAIN:
  the only error test in the visible file asserts with `try/except/else: raise
  AssertionError`, which 1.0.1 wrongly treated as "asserts nothing".

## Judge bugs found by this evaluation (fixed after all runs, in 1.0.2)

1. Vacuous-test false positives: tests that reach the code through a helper or fixture in
   the test file (`make_book()`), or assert via `raise AssertionError`, `pytest.fail` or
   `self.assert*`, were discarded (commits `6133cce`, `92b7728`).
2. A re-freeze after the code erased the independence of tests unchanged since an earlier
   freeze (commits `0335ba2`, `95817b9`). On T4 r4/r5 and T5 r1 only the corrected
   test(s) now lose independence (1, 2 and 1), and 27, 33 and 24 tests remain independent.

The judge code was not changed between the first and last agent run of this evaluation.

## Deviations from the protocol

- **Run 4 aborted and repeated.** All 12 run-4 agents stopped mid-task on an API usage
  limit (HTTP 429), before any of them called the judge. Their partial workspaces are
  archived in `eval2/aborted_r4_ratelimit/`; the workspaces were reset from the frozen
  benchmark and run 4 was relaunched fresh. The protocol counts agent crashes as 0%;
  this was a quota failure that hit both conditions equally before completion, so it was
  treated as an infrastructure failure. Counting those 12 runs as 0% would change both
  means equally (D unchanged).
- **Agents running the wrapper wrongly.** Several B agents first ran the wrapper without
  the Python interpreter (no verdict, no effect) and one ran it from another directory
  (see T3 B r4 above). One run-1 agent wrote a file outside its workspace
  (`ws2/T5_verify2.json`).
- **Task author.** The independent author agent was stopped by the user after it had
  written and validated all six tasks; the evaluator re-validated them (0 invalid) and
  froze them without edits.
- **Leakage check.** No workspace file references the hidden test directory or
  `eval_results`. Hidden tests were copied to `eval2/benchmark/hidden/` only after all
  runs; all 61 benchmark files match their pre-run SHA-256 hashes.

## Conflict of interest

The evaluator (an AI assistant) also modified the judge. Mitigations as in the protocol:
independent task author, protocol and benchmark hash-frozen before any run, scripted
scoring, no judge change during the runs, all raw outputs published.

## Recommendation

**Ship with a lowered claim.** 1.0.1 works as a guard: it never gave a false FAIL, never
let an agent weaken a test, tracked iterations and stopped cleanly. But it did not make
the agent's code more correct; it cost 25% more tokens and 2.8x the wall time, and on
the one case where the agent's code was wrong, it said PASS. The README must not claim
that it improves an agent's code. 1.0.2 adds a requirements checklist and mutation
feedback that target exactly that gap; whether they help is the question of
evaluation 3, on harder tasks with real baseline headroom.
