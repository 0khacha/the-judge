# CLAUDE.md — The Judge

## Context loading (read this first on every session)

1. Read `AGENT_CONTEXT.md` — stable project map (architecture, conventions).
2. Read `AGENT_STATE.md` — current project state (phase, known bugs, next tasks).
3. Use those files as your primary project map.
4. Open only the specific files relevant to the current task.
5. Do **not** scan the entire repository unless the task explicitly requires it.

## Token efficiency

- Do not re-read files already in context.
- Do not repeat information already present in context files.
- Prefer `grep`/targeted search over broad directory listing.
- Summarize large command outputs — do not dump them raw into context.
- Use existing evidence; do not re-discover already known facts.
- Keep reasoning focused on the current task.

## Project conventions

| Area | Convention |
|---|---|
| Package | `the_judge/` (canonical); `judge/` is a backward-compat shim |
| Entry point | `the_judge/api.py` → `verify()`, `improve()`, `critique()` |
| CLI | `judge` command → `the_judge/integrations/cli.py` |
| Line length | 100 characters |
| Formatter | `ruff format` |
| Linter | `ruff check` + `mypy` |
| Tests | `pytest tests/` |
| Python | ≥3.9 |

## Validation workflow (always run after behavioral changes)

```
judge verify . --json   # machine-readable; parse decision + findings[].suggested_focus
```

- PASS (exit 0) → done.
- FAIL (exit 1) → fix using `findings[].suggested_focus`, re-verify. Max 5 rounds.
- ABSTAIN (exit 2) → add tests that exercise the unverified behavior, re-verify.
- ERROR (exit 3) → check workspace path.

Other useful commands:
```
pytest tests/ -v            # run test suite directly
ruff check the_judge/ tests/
mypy the_judge/
make test                   # shorthand
```

## Critical constraints

- **Never** modify files inside `the_judge/core/` without explicit user approval — it is the verifier.
- **Never** claim code works without running `judge verify .` first.
- **Never** skip verification because "the change is small."
- **Never** modify unrelated files.
- Parse JSON output from `judge verify . --json`; do not regex-scrape human-readable output.

## Context maintenance

| File | Content | Update when |
|---|---|---|
| `AGENT_CONTEXT.md` | Stable architecture + conventions | Structure or conventions change |
| `AGENT_STATE.md` | Current state snapshot | Significant implementation changes occur |

Rules:
- Never blindly rewrite either file.
- Never put raw logs or large code snippets into them.
- Update `AGENT_STATE.md` after completing features, fixing bugs, or changing the phase.
- Update `AGENT_CONTEXT.md` only when stable architecture or directory structure changes.
