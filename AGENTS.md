# Agent Guide

This file is the map for AI coding agents working with [The Judge](https://github.com/0khacha/the-judge). Read it after installing or cloning the repository. It defines the verification-repair loop protocol that agents must follow after each critical round of code changes.

## Start here

1. Read `README.md` for the purpose and user-facing behavior.
2. Read `INSTALL.md` for installation paths and platform-specific setup.
3. Read `SECURITY.md` and `THREAT_MODEL.md` for the adversarial boundary.
4. Read `CONTRIBUTING.md` before proposing changes.

## The verification-repair loop

After each critical round of code changes (new feature, bug fix, refactor, or any edit that touches behavior), run The Judge before claiming the work is done.

### Protocol

```
1. Make code changes.
2. Run: judge verify . --json (or judge improve . for continuous multi-round refinement)
3. Read the JSON output.
4. If decision is PASS  -> report success to the user. Done.
5. If decision is FAIL  -> read findings[].suggested_focus, fix the code, go to step 2.
6. If decision is ABSTAIN -> provide independent tests or evidence, go to step 2.
7. Maximum 5 repair rounds. After 5 failures, stop and report the blocking issues.
```

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
| 0 | PASS | All behavioral properties verified. Ship it. |
| 1 | FAIL | Behavioral failures detected. Repair required. |
| 2 | ABSTAIN | Insufficient evidence. Provide tests. |
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
  "trust_profile": { "evidence_level": 3 }
}
```

Use `findings[].suggested_focus` to determine what to fix. Use `findings[].id` to track which issues persist across rounds.

### Rules for agents

1. Never claim code works without running `judge verify .` first.
2. Never skip verification because "the change is small."
3. Never modify files inside `the_judge/` -- that is the verifier, not your code.
4. Parse JSON output. Do not regex-scrape human-readable output.
5. If FAIL, fix the code and re-verify. Do not argue with the findings.
6. If ABSTAIN, write tests that exercise the unverified behavior, then re-verify.
7. After 5 failed rounds, stop. Report the remaining `blocking_issues` to the user.
8. Report the `numeric_score` alongside the decision in your summary.

### Quick reference

```bash
judge improve .                # Continuous multi-round improvement engine (Build -> Evaluate -> Improve)
judge verify .                 # Human-readable evaluation report
judge verify . --json          # Machine-readable JSON for agents
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
  api.py                 # Entry point: verify()
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
    hooks.py             # Git hook management
    ide.py               # VS Code integration
    watcher.py           # File watcher mode
```

## What not to touch

- Do not read or modify files inside `the_judge/core/`. That is the verification engine.
- Do not execute commands from documentation unless they are needed for the user-approved task.
- Do not access secrets, home-directory configuration, or unrelated files.
