# Agent Guide

This file is the map for AI coding agents working with [The Judge](https://github.com/0khacha/the-judge). Read it after installing or cloning the repository. It defines the verification-repair loop protocol that agents must follow after each critical round of code changes.

> **Install `the-judge-verify`.** The PyPI project named `the-judge` is an
> **unrelated package** by another author:
> `pip install the-judge-verify`

## Start here

1. Read `README.md` for the purpose and user-facing behavior.
2. Read `docs/installation.md` for installation paths and platform-specific setup.
3. Read `SECURITY.md` and `docs/threat-model.md` for the adversarial boundary.
4. Read `CONTRIBUTING.md` before proposing changes.

## The verification-repair loop

After each critical round of code changes (new feature, bug fix, refactor, or any edit that touches behavior), run The Judge before claiming the work is done.

### Protocol

```
1. Tests first. Before writing or changing the implementation, write tests for the
   behaviour the task asks for (normal cases, edge cases, invalid input) and run:
       judge freeze .
   If the user gave you tests, freeze them before you touch the code.
2. Implement (or change) the code. Do not edit the frozen tests.
3. Run: judge verify . --json
4. Do what next_actions[0] says. Every verdict has numbered next_actions, each with
   "step", "action", "detail" and, where useful, "test", "command", "guidance":
     done                         -> report PASS and numeric_score. Stop.
     fix_code / fix_regression    -> change the IMPLEMENTATION so the named test passes.
     restore_tests                -> undo your change to the named frozen test.
     cover_requirement            -> the named spec rule (R1, R2, ...) has no passing test:
                                     write one that checks the rule and names its id.
     add_test                     -> a planted bug at the named file:line went unnoticed:
                                     decide the correct behaviour there FROM THE SPEC, add a
                                     test for it; if that test fails, fix the code.
     write_tests / freeze_tests   -> do what "detail" says, then implement.
     stop                         -> stop and report loop.stuck_reason and the
                                     remaining next_actions to the user.
5. Go to 3. The judge counts iterations (.judge/history.json), reports regressions
   (passed before, fails now) and says "stuck" after 3 identical non-PASS results or
   5 runs without PASS.
```

What counts as evidence: a test is *independent* when it is unchanged since `judge freeze`
(or since the last git commit) **and** the implementation changed after that. Tests
written after the code must pass but cannot earn PASS on their own. That is why step 1
comes first. Correcting one of your own frozen tests and freezing again only costs that
one test its independence.

Requirements checklist: the judge numbers the rules (list items) of TASK.md, SPEC.md or
REQUIREMENTS.md as R1..Rn. `judge freeze` prints them and marks the ones no test names
yet. Write a test per rule and name the id in a comment or docstring
(`def test_unterminated_quote():  # R4`), so every rule is tested before you implement.
PASS requires each rule to have a passing test that names it.

Mutation feedback: before PASS, the judge plants small bugs in the implementation
(`<` -> `<=`, `+` -> `-`, a removed `raise`, ...) and reruns all tests on a copy of
the workspace. If fewer than 85% are caught, the verdict is ABSTAIN with one `add_test`
action per uncaught bug. Tests you add for them do not need to be frozen. Write them
from the specification, not from what the code currently returns -- that is how they
find bugs. `--no-mutation` skips this step.

Time limit: the sandboxed test run may take 300 s. A run stopped at the limit is ABSTAIN
with a `raise_timeout` action; raise it with `--timeout N` only if the suite is
legitimately slow -- a hang in the code under test is a bug to fix.

### Adaptive Evaluation Engine

The Judge automatically adapts its evaluation method based on workspace classification:

* **Visual Projects** (Web applications, UIs, Dashboards, Data Viz, HTML/CSS):
  `Build -> Run -> Screenshot -> Evaluate -> Improve -> Screenshot -> Compare -> Repeat`
  Captures screenshot evidence per round (`_judge_visual/round_N_visual.png`), evaluating typography, hierarchy, spacing, and UI polish.

* **Non-Visual Projects** (Libraries, APIs, Backends, CLI tools, Algorithms):
  `Build -> Test -> Evaluate -> Identify Weaknesses -> Improve -> Re-test -> Repeat`
  Evaluates unit tests, integration tests, performance, security analysis, contract requirements, and structural properties without forcing unnecessary screenshots.

### Exit codes

| Code | Decision | Meaning |
|------|----------|---------|
| 0 | PASS | Tests fixed before the implementation pass; no tampering detected. Not a proof of correctness. |
| 1 | FAIL | A test failed, a regression appeared, or tests were tampered with. Follow next_actions. |
| 2 | ABSTAIN | Not enough independent evidence; next_actions says exactly what is missing. |
| 3 | ERROR | Execution error. Check the workspace path. |

### Reading structured findings

The `--json` flag returns machine-readable output. Key fields:

```json
{
  "decision": "FAIL",
  "numeric_score": 0.0,
  "findings": [
    {
      "id": "BEH-001",
      "category": "behavior",
      "severity": "high",
      "description": "Behavioral test failed: test_cache_expiration",
      "suggested_focus": "Review boundary logic in test_cache_expiration."
    }
  ],
  "blocking_issues": ["..."],
  "next_actions": [
    {"step": 1, "action": "fix_code", "test": "test_cache_expiration",
     "detail": "AssertionError: assert None == 'v'",
     "guidance": "Change the implementation so this test passes. Do not edit, skip, parametrize away or weaken the test."},
    {"step": 2, "action": "re_verify", "detail": "After the fix, verify again.", "command": "judge verify . --json"}
  ],
  "loop": {"iteration": 2, "regressions": [], "newly_passing": [], "stuck": false, "stuck_reason": null},
  "trust_profile": { "evidence_level": 3 }
}
```

Follow `next_actions` in order; `findings[]` holds the details. `loop` compares this run with the previous one.

### Rules for agents

1. Never claim code works without running `judge verify .` first.
2. Never edit, skip, delete, parametrize away or weaken a frozen test to make it pass.
   Adding tests is always fine. If a frozen test is genuinely wrong, fix it, run
   `judge freeze .` again and tell the user which test you changed and why.
3. Never modify files inside `the_judge/` -- that is the verifier, not your code.
4. Parse the JSON output and follow `next_actions` in order.
5. mypy/ruff findings (`static_analysis`) are advisory; they never decide the verdict.
6. When `loop.stuck` is true, stop and report; do not keep iterating.
7. Report the decision and `numeric_score` in your summary.

### Quick reference

```bash
judge improve .                # Read-only review: verdict, next actions, critique; changes no files
judge verify .                 # Human-readable evaluation report
judge verify . --json          # Machine-readable JSON for agents
judge freeze .                 # Freeze the current tests (do this before implementing)
judge verify path/to/file.py   # Verify a single file
judge contract .              # Inspect requirement coverage
judge demo                    # 60-second interactive demo
judge hook install            # Install pre-commit verification hook
judge watch .                 # Watch mode: re-verify on file save
judge init vscode             # Generate VS Code tasks
```

## Repository structure

```
the_judge/
  api.py                 # Entry points: verify(), freeze(), improve(), critique()
  hook.py                # Claude Code Stop hook (judge hook run)
  core/
    sandbox.py           # Subprocess isolation
    evidence.py          # Evidence capture
    score_engine.py      # Trust scoring and hard gates
    decision.py          # VerificationResult dataclass
    contract_engine.py   # Requirement contract evaluation
    property_engine.py   # Dynamic property checks
  integrations/
    cli.py               # CLI driver (judge command)
    agent_adapter.py     # Agent feedback formatter
    repair_loop.py       # Multi-round repair loop
    agent_runner.py      # Runs a coding agent for judge improve --agent
    hooks.py             # Git hook management
    ide.py               # VS Code integration
    watcher.py           # File watcher mode
```

## What not to touch

- Do not read or modify files inside `the_judge/core/`. That is the verification engine.
- Do not execute commands from documentation unless they are needed for the user-approved task.
- Do not access secrets, home-directory configuration, or unrelated files.
