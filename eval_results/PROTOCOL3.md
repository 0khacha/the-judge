# Evaluation 3 protocol (pre-registered)

Written and SHA-256-hashed before any evaluation-3 task exists and before any agent run.
Hash in `PROTOCOL3.sha256`. Deviations are reported in REPORT3.md under "Deviations".

## Question

Does the-judge-verify 1.0.2 (requirements checklist + mutation feedback), used as its
AGENTS.md prescribes, make a coding agent's final code more correct on hidden tests than
the same agent without it, by at least 40%?

## Judge under test

Wheel `the_judge_verify-1.0.2-py3-none-any.whl`, SHA-256
`3f8e624c64fe69983a5acef80b54af2ae85e68c70034d10332037084a1f1d56e` (commit `1a3bfa1`),
installed into a fresh venv. No change to the judge from the first pilot run to the
last main run.

## Conflict of interest

The evaluator (an AI assistant) built the judge, knows evaluation 2's tasks and hidden
tests, and wants the result to be positive. Mitigations: the judge is frozen and hashed
before the tasks exist; tasks are written by a separate agent session that does not read
this repository and is told nothing about how the judge works; scoring is scripted; the
pilot selects tasks using baseline runs only; all raw outputs are published.

## Tasks

- 9 candidate tasks, written by an independent author agent. Brief: realistic Python
  tasks that a capable model often gets partly wrong; each with a TASK.md stating every
  requirement the hidden tests check (no format is prescribed), at least 8 distinct
  checked requirements, 2-3 visible tests in `test_visible.py`, 25+ hidden tests, a
  reference solution and two wrong solutions that pass the visible tests and fail hidden
  tests; at least 3 tasks multi-file. The author validates; the evaluator re-validates
  and drops (never fixes) invalid tasks.
- Hidden tests, references and wrong solutions live outside every agent workspace and are
  hash-frozen with the public files before the pilot.

## Pilot (task selection, baseline only)

2 runs of condition A per candidate task (18 runs). Keep the 6 tasks with the lowest
pilot mean hidden pass rate (ties: fewer fully-correct pilot runs, then task id), among
those with pilot mean <= 95%. If fewer than 6 qualify, keep all qualifying if >= 4;
otherwise stop and report "insufficient headroom". Pilot runs are reported and not
scored in the main result. Selecting on baseline runs only affects both conditions
equally; the main runs are fresh.

## Conditions (main runs)

- Model: Claude Haiku, every run. 6 tasks x 2 conditions x 5 runs = 60 runs.
- **A**: the evaluation-2 A prompt, unchanged (workspace path substituted).
- **B**: the A prompt plus the 1.0.2 AGENTS.md protocol quoted verbatim (steps 1-5, the
  evidence, requirements-checklist and mutation paragraphs, the rules for agents), plus a
  logging wrapper as the only way to call the judge (`freeze`, `verify . --json`). At most
  8 verify calls; freeze calls are not counted.
- Fresh workspaces outside the repository for every run.

## Metrics

1. Hidden-test pass rate of the final workspace (primary), scored on the agent's non-test
   files only, in a clean directory.
2. Fully correct runs (100% hidden).
3. Failure rate F = 1 - hidden pass rate; per condition, mean over runs.
4. B: verify calls, iterations to first PASS, final decision, counts of
   `cover_requirement` and `add_test` actions, and how often a verify after such an
   action was a FAIL (a test the agent added exposed a bug).
5. Regressions, tokens, wall time, judge false PASS / false FAIL (as in evaluation 2).
6. Judge accuracy without agents: reference and wrong solutions with the visible tests
   frozen first.

## Decision rules (fixed in advance)

D = mean hidden pass rate(B) - mean hidden pass rate(A); RR = (F_A - F_B) / F_A, the
relative reduction of hidden-test failures; CI = 95% bootstrap interval of D (10,000
resamples, runs resampled within task x condition).

- **Goal met (>= 40% better)**: RR >= 0.40 AND CI excludes 0 AND B has no more
  fully-incorrect runs than A.
- **Improvement below goal**: D > 0 and CI excludes 0, goal not met.
- **No evidence**: CI includes 0 or D <= 0 (reported as negative/null).

Reported regardless: per-task results, cost ratios, false PASS/FAIL, judge accuracy.

## What will not be done

No change to tasks, hidden tests, prompts, judge or decision rules after the first pilot
run. No rerun of unfavourable runs. Runs that crash because of the agent count as 0%.
Runs stopped by an infrastructure failure before completion (API quota, harness error)
are archived and rerun fresh, for whichever condition was affected, and reported. If the
goal is not met, any further change to the judge is evaluated on new tasks (evaluation
4), never on these.
