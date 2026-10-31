# Evaluation

The Judge's claims are tested in pre-registered evaluations with Claude Haiku as the
coding agent. Each has its protocol hashed before any task existed, plus raw data and a
report: [eval_results/](../eval_results/README.md).

Summary:

- **Does it make an agent's code more correct?** Not shown. On every benchmark tried
  (small tasks, harder tasks with 41-149 hidden tests, change requests in existing
  projects with hidden regression tests), the agent without the judge already passed
  all hidden tests in 65 of 66 runs, leaving nothing to improve.
- **Is it accurate as a gate?** 1.0.1 gave PASS to 10 of 12 wrong solutions
  (evaluation 2). 1.0.2, with the requirements checklist and mutation feedback, gave
  PASS to none in 45 checks (evaluations 3-4) and never gave a false FAIL there. No
  agent weakened a frozen test.
- **Cost.** Correct code gets ABSTAIN until each spec rule has a test, and mutation adds
  10-20 s per verify on a small project.

Earlier documents in this repository cited "v3.2/v4.x" benchmark numbers. They came
from a simulated benchmark, have been removed, and should not be relied on.

`tests/regression_audit/` is a labelled corpus (correct and incorrect solutions per task)
for checking that changes to the judge do not make it less discriminating:
`python tests/regression_audit/run_audit.py`.
