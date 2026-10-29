# Evaluation 4: stopped at the pilot -- insufficient headroom

Pre-registered in [`PROTOCOL4.md`](PROTOCOL4.md) (hashed 2026-10-29T16:23:49Z, before any
task existed). Raw data: [`eval4/`](eval4/).

## Result

Setting: change requests in existing multi-module projects with partial test suites;
hidden tests check the change (`test_new_*`) and existing behaviour the change could
break (`test_reg_*`). The baseline agent (Claude Haiku, no judge) solved everything:

| Task | Change | Hidden (new/reg) | Pilot A r1 | Pilot A r2 |
|---|---|---|---|---|
| D1_library | premium member tier | 26/17 | 43/43 | 43/43 |
| D2_shop | coupons | 28/13 | 41/41 | 41/41 |
| D3_tracker | recurring tasks | 30/16 | 46/46 | 46/46 |
| D4_templates | if / filter args / loop var | 33/14 | 47/47 | 47/47 |
| D5_bank | overdraft | 29/11 | 40/40 | 40/40 |
| D6_cache | weighted entries | 29/13 | 42/42 | 42/42 |
| D7_config | env overrides | 29/12 (48 cases) | 48/48 | 48/48 |
| D8_rooms | buffer between bookings | 20/16 | 36/36 | 36/36 |
| D9_etl | composite key, keep last | 26/17 | 43/43 | 43/43 |

18 of 18 pilot runs fully correct, on new behaviour and regressions alike. Per the
pre-registered rule the evaluation stopped with "insufficient headroom"; no main runs.
Scorer check: on D2, the two hand-written wrong solutions score 28/41 and 40/41, and the
unchanged project fails.

## Judge accuracy (no agent; project tests frozen first, then the solution added)

All 27 solutions (9 references, 18 wrong): ABSTAIN with `cover_requirement` first -- the
project tests do not name the ticket's rules. 0 false PASS, and also no PASS for the
correct references until tests for the rules exist.

## Deviations

- Projects are 170-285 lines (protocol: roughly 300-900). Kept, since smaller projects
  can only reduce headroom, and reported here.
- The author loosened one exact-match public assertion in D2, D6 and D9 because the
  ticket changes those outputs.
- Harness fix after the pilot runs, before scoring: the visible-test check read
  `test_visible.py`, which evaluation-4 projects do not have; it now runs the original
  `tests/*.py`. This affects only the `visible_pass` column, not the hidden scores.

## Conclusion across evaluations 2-4

| Evaluation | Setting | Baseline runs fully correct |
|---|---|---|
| 2 | 6 small tasks | 29 / 30 |
| 3 | 9 harder tasks, 41-149 hidden tests | 18 / 18 (pilot) |
| 4 | 9 change requests in existing projects | 18 / 18 (pilot) |

When the requirements are written down, Claude Haiku already produces code that passes
every hidden test. Measured on such tasks, a verifier cannot make it better, and a
"40% better" claim can be neither supported nor refuted. **Hold the claim.** What can
be stated from the data: 1.0.2 never PASSed a wrong solution in 45 judge-accuracy
checks (evaluations 3-4), where 1.0.1 PASSed 10 of 12 in evaluation 2.
