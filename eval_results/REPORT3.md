# Evaluation 3: stopped at the pilot -- insufficient headroom

Pre-registered in [`PROTOCOL3.md`](PROTOCOL3.md) (SHA-256 in `PROTOCOL3.sha256`, hashed
2026-10-29T14:42:52Z, before any task existed). Raw data: [`eval3/`](eval3/).

## Result

The question was whether the-judge-verify 1.0.2 (requirements checklist + mutation
feedback) makes Claude Haiku's code at least 40% better on hidden tests. **It could not be
measured.** The protocol selects tasks on which the baseline agent fails sometimes; in
the pilot the baseline failed nothing:

| Task | Hidden tests | Pilot A r1 | Pilot A r2 |
|---|---|---|---|
| C1_duration | 103 | 103/103 | 103/103 |
| C2_ratelimit (package) | 41 | 41/41 | 41/41 |
| C3_csv | 73 | 73/73 | 73/73 |
| C4_semver | 149 | 149/149 | 149/149 |
| C5_invoice (package) | 105 | 105/105 | 105/105 |
| C6_cron | 105 | 105/105 | 105/105 |
| C7_wrap | 71 | 71/71 | 71/71 |
| C8_template (package) | 120 | 120/120 | 120/120 |
| C9_workflow | 115 | 115/115 | 115/115 |

18 of 18 pilot runs were fully correct (mean 53.6k tokens, 257 s per run). No task met
the "pilot mean <= 95%" rule, so, as pre-registered, the evaluation stopped with
"insufficient headroom" and no main runs were made. The tasks were not changed or
replaced after the pilot.

Scorer sanity check: on C4 a wrong solution scores 126/149 and an empty workspace 0%;
the pilot code (332 lines, written by the agent) scores 149/149.

## Judge accuracy (no agent; visible tests frozen first, then the solution added)

| | Reference (correct) | Wrong solutions (18) |
|---|---|---|
| 1.0.1 on eval-2 tasks | PASS 5/6 | PASS 10/12 (false PASS) |
| 1.0.2 on eval-3 tasks | ABSTAIN 9/9 | ABSTAIN 18/18 (0 false PASS) |

1.0.2 numbered 7-24 rules per TASK.md, and the visible tests name none of them, so every
verdict was ABSTAIN with `cover_requirement` first. That is the intended behaviour: the
judge no longer says PASS on code whose spec rules are untested, but correct code also
needs the tests to be written before it can PASS. Mutation feedback did not run (it runs
only when everything else says PASS).

## What this means

On self-contained tasks whose TASK.md states every requirement, Haiku already writes
correct code without help. Both earlier evaluations show the same ceiling (evaluation 2:
29/30 baseline runs fully correct). A verifier can only improve code that is wrong, so a
"40% better" claim cannot be supported -- or refuted -- on this kind of task. Headroom
for the baseline would need different conditions: larger or under-specified projects,
changes to existing code with regressions to avoid, or a tighter budget.

## Deviations

- The task author wrote wrong solutions as scripted patches of the reference
  (`benchmark/hidden/_tools/`), not as independently written code. They are used only for
  the judge-accuracy table.
- None in the pilot itself; no rate-limit interruptions.

## Conflict of interest

As in evaluation 2: the evaluator built the judge. Mitigations: judge frozen and hashed
before the tasks existed; independent task author with no access to this repository;
scripted scoring; baseline-only task selection; raw outputs published.

## Recommendation

**Hold the "improves agent code" claim.** 1.0.2 is a stricter and more accurate gate
(0 false PASS on 18 wrong solutions, where 1.0.1 had 10), but there is still no
measurement showing that an agent writes better code with it, because on these tasks
the baseline has nothing left to improve.
