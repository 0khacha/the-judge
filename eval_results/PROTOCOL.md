# Evaluation 2 protocol (pre-registered)

Written and SHA-256-hashed before any task existed and before any agent ran. The hash
is in `PROTOCOL.sha256`. Any deviation is reported in REPORT2.md under "Deviations".

## Question

Does the-judge-verify 1.0.1, used as AGENTS.md prescribes, make a coding agent's final
code more correct (on hidden tests) than the same agent without it?

## Conflict of interest

The evaluator (this assistant) changed the judge being evaluated. Mitigations: (1) the
tasks, hidden tests, reference and wrong solutions are written by a separate agent
session that is instructed not to read the judge's repository; (2) this protocol and the
benchmark are hash-frozen before any run; (3) scoring is done by scripts against hidden
tests; (4) the judge's code is not changed between the first and last run; (5) all raw
outputs are saved under `eval_results/eval2/`.

## Subjects and conditions

- Model: **Claude Haiku** for every agent run (smaller than the earlier Sonnet runs, to
  leave headroom). Same base prompt in both conditions.
- **A (baseline)**: workspace with TASK.md, the visible tests and any starter files. The
  agent may run the visible tests with pytest. No judge.
- **B (skill)**: same workspace and prompt, plus the AGENTS.md protocol of 1.0.1 quoted
  verbatim, and a `judge` command (logging wrapper around the installed 1.0.1 build that
  snapshots the workspace and stores the full JSON for every call). `judge freeze` calls
  are logged but do not count as iterations. At most 5 `judge verify` calls; a 6th call
  is refused by the wrapper.
- The judge is installed from the locally built 1.0.1 wheel (not published), into a
  venv; mypy/ruff are whatever is on PATH, identical for both conditions.
- 6 tasks x 2 conditions x **5 runs** = 60 agent runs, all in fresh workspaces outside
  the repository. Hidden tests live outside every workspace and are copied into
  `eval_results/eval2/` only after all runs.

## Benchmark requirements (given to the task author)

6 tasks, at least 2 multi-file, at least 3 traps (obvious solution passes visible tests
but fails hidden tests, with the checked requirement stated in TASK.md). Each task has a
reference solution and two wrong solutions that pass the visible tests and fail the
hidden tests; the author validates this. The evaluator re-validates before freezing and
does not edit the tasks. If a task fails re-validation it is dropped (not fixed) and the
drop is reported.

## Metrics (per run, then per condition)

1. **Hidden-test pass rate** of the final workspace: hidden tests run against the
   agent's non-test files only, in a clean directory (primary metric).
2. Fully correct runs: hidden pass rate == 100%.
3. **Iterations** (B): number of `judge verify` calls; **iterations to PASS**: index of
   the first PASS, if any.
4. **Regressions** (B): a hidden test that passes in one judged snapshot and fails in the
   next snapshot or the final workspace.
5. Tokens and wall time per run (harness totals).
6. **Judge false PASS**: a judge PASS on a snapshot whose code fails any hidden test.
   **Judge false FAIL**: a judge FAIL on a snapshot whose code passes all hidden tests.
7. **Actionable ABSTAIN fraction**: an ABSTAIN counts as acted on if the next judge call
   in the same run has a different decision or more independent tests; an ABSTAIN that is
   the last call of the run counts as not acted on.
8. Separately (no agent): judge verdict on each task's reference and wrong solutions with
   the visible tests frozen before the implementation is added (judge accuracy).

## Decision rules (fixed in advance)

Let D = mean hidden pass rate(B) - mean hidden pass rate(A), over all 30 + 30 runs, and
CI = 95% bootstrap interval of D (10,000 resamples, runs resampled within each task and
condition).

- **Clear improvement**: D >= 10 percentage points AND the CI excludes 0 AND B has no
  more fully-incorrect final runs than A AND judge false PASS = 0.
- **Marginal**: D > 0 and not "clear improvement", with D >= 3 points.
- **No evidence**: D < 3 points, or D negative (reported as a negative result).

Reported regardless of the rule: per-task results (to show headroom: a task where A is
100% in all 5 runs has no headroom), cost ratios, false PASS/FAIL, actionable ABSTAIN.

## What will not be done

No change to tasks, hidden tests, prompts, judge code or decision rules after the first
agent run. No re-running of unfavourable runs. Agent runs that crash or time out are
reported and count as 0% hidden pass rate.
