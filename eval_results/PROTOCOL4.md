# Evaluation 4 protocol (pre-registered)

Written and SHA-256-hashed before any evaluation-4 task exists and before any agent run.
Hash in `PROTOCOL4.sha256`. Deviations are reported in REPORT4.md under "Deviations".

## Why a fourth evaluation

Evaluations 2 and 3 had no headroom: the baseline agent solved self-contained, fully
specified tasks completely (29/30 and 18/18 runs). Evaluation 4 uses the setting where
agents are known to fail more often: **changing an existing codebase** without breaking
behaviour that the visible tests do not cover.

## Question

Does the-judge-verify 1.0.2, used as its AGENTS.md prescribes, make a coding agent's
final code more correct on hidden tests -- new behaviour plus existing behaviour
(regressions) -- than the same agent without it, by at least 40%?

## Judge under test

Unchanged from evaluation 3: wheel `the_judge_verify-1.0.2-py3-none-any.whl`, SHA-256
`3f8e624c64fe69983a5acef80b54af2ae85e68c70034d10332037084a1f1d56e`, in the same venv. No
change to the judge from the first pilot run to the last main run.

## Conflict of interest

As in evaluation 3 (the evaluator built the judge). Same mitigations: judge frozen before
the tasks exist, independent task author without access to this repository and told
nothing about the judge, scripted scoring, baseline-only task selection, raw outputs
published.

## Tasks

9 candidate tasks by an independent author agent. Each task is an existing small Python
project (several modules, roughly 300-900 lines, with an existing partial test suite in
the workspace) plus a TASK.md change request (a feature, behaviour change or bug fix that
touches more than one module). Hidden tests check (a) every requirement of the change
request and (b) existing behaviour of the project that the change could break and that
the workspace tests do not fully cover. Per task: reference (the changed project), two
plausible wrong solutions that pass the workspace tests and fail hidden tests, 30+
hidden tests, validation by the author, re-validation by the evaluator (invalid tasks are
dropped, never fixed). Hidden files live outside every workspace and are hash-frozen
with the public files before the pilot.

## Pilot, conditions, metrics, decision rules

Identical to [`PROTOCOL3.md`](PROTOCOL3.md): pilot of 2 baseline runs per candidate; keep
the 6 lowest pilot means among those <= 95% (at least 4, else stop with "insufficient
headroom"); main runs 6 tasks x 2 conditions x 5 runs with Claude Haiku; the A prompt of
evaluations 2-3 and the B prompt of evaluation 3 (1.0.2 AGENTS.md protocol quoted
verbatim, logging wrapper, at most 8 verify calls). Metrics as in PROTOCOL3, plus the
hidden pass rate split into new-behaviour tests and regression tests where the author's
labels allow it.

- **Goal met (>= 40% better)**: RR = (F_A - F_B) / F_A >= 0.40 AND the 95% bootstrap CI
  of D = pass(B) - pass(A) excludes 0 AND B has no more fully-incorrect runs than A.
- **Improvement below goal**: D > 0 and CI excludes 0, goal not met.
- **No evidence**: CI includes 0 or D <= 0.

## What will not be done

No change to tasks, hidden tests, prompts, judge or decision rules after the first pilot
run; no rerun of unfavourable runs; agent crashes count as 0%; infrastructure failures
(API quota, harness error) before completion are archived and rerun fresh and reported.
If the goal is not met, any further judge change is evaluated on new tasks.
