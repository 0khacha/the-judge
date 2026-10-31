---
name: judge-loop
description: Test-first verify-repair loop with The Judge (`judge` CLI from the-judge-verify). Use when implementing or changing behaviour in a project that has a .judge/ folder, a TASK.md/SPEC.md/REQUIREMENTS.md, or a judge.json, and whenever the user asks to "verify with the judge", "run the judge", "make it pass the judge", "freeze the tests", or to prove a change works before calling it done.
---

# The Judge: verify-repair loop

The Judge is an independent verifier. It runs the project's tests in a sandbox, refuses
tests that were weakened or written to fit the code, plants small bugs (mutation testing)
to find behaviour no test checks, and answers with PASS / FAIL / ABSTAIN plus numbered
`next_actions`. Never claim the work is done before it says PASS.

## Setup (once)

```bash
judge --version || pip install the-judge-verify
```

The PyPI package `the-judge` is unrelated; install `the-judge-verify`.

## Loop

1. **Tests first.** Before changing the implementation, write tests for the requested
   behaviour: normal cases, edge cases and invalid input. Take expected values from the
   spec, not from the code. For every rule of TASK.md / SPEC.md / REQUIREMENTS.md (the
   judge numbers list items R1..Rn), write a test and name the id in a comment:
   `def test_unterminated_quote():  # R4`. If the user gave tests, use those.
2. **Freeze:** `judge freeze .` It lists the rules no test names yet; cover them first.
3. **Implement.** Do not edit frozen tests.
4. **Verify:** `judge verify . --json`
5. **Do what `next_actions[0]` says**, then go back to 4:

| action | what to do |
|---|---|
| `done` | Report PASS and `numeric_score`. Stop. |
| `fix_code`, `fix_regression` | Change the IMPLEMENTATION so the named test passes. |
| `restore_tests` | Undo your change to the named frozen test. |
| `cover_requirement` | Write a test for that spec rule that names its id. |
| `add_test` | A planted bug at `file:line` went unnoticed. Decide the correct behaviour there from the spec, add a test; if it fails, fix the code. |
| `write_tests`, `freeze_tests` | Do what `detail` says, then implement. |
| `raise_timeout` | Only if the suite is legitimately slow: `--timeout N`. A hang is a bug. |
| `stop` | Stop iterating; report `loop.stuck_reason` and the remaining actions to the user. |

## Rules

- Never edit, skip, delete, parametrize away or weaken a frozen test. If one is truly
  wrong, fix it, run `judge freeze .` again and tell the user which test and why.
- Adding tests is always fine.
- mypy/ruff findings (`static_analysis`) are advisory.
- Never modify files inside a `the_judge/` package or `.judge/`.
- In the summary, report the decision and `numeric_score`.

## The Stop hook

With this plugin enabled, when you finish a turn in a project that has `.judge/`, the
judge verifies the changed code. If the verdict is not PASS, your turn is sent back with
its next actions as the reason: act on them as in step 5. If nothing changed since the
last check, or the judge reports the loop as stuck, you may stop.
