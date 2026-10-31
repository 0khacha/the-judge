# The Judge: plugin and integration guide

The Judge is a verifier, not a code generator: it runs your tests in a sandbox, refuses
evidence that was weakened or fitted to the code, plants small bugs to find behaviour no
test checks, and answers PASS / FAIL / ABSTAIN with numbered `next_actions`. An agent
(Claude Code, Cursor, Codex, ...) makes the changes; The Judge decides whether they are
done. Installation per tool: [INSTALL.md](INSTALL.md).

## 1. Claude Code plugin

```bash
pip install the-judge-verify
```

```text
/plugin install the-judge --marketplace 0khacha/the-judge
```

| Component | What it does |
|---|---|
| Stop hook (`hooks/hooks.json`) | At the end of each turn, verifies the project if it changed; unless PASS, sends the turn back with the next actions. |
| Skill `judge-loop` | The test-first protocol: write tests, `judge freeze`, implement, verify, follow `next_actions`. |
| `/the-judge:freeze` | Freeze the tests and show spec rules no test names yet. |
| `/the-judge:verify` | Verify and work through `next_actions` until PASS. |
| `/the-judge:improve` | Read-only review, most important issue first. |

### How the Stop hook decides

1. **Opt-in per project.** It acts only where `.judge/` exists (created by
   `judge freeze`). `THE_JUDGE_HOOK=always` enables it everywhere, `THE_JUDGE_HOOK=off`
   disables it.
2. **Only after changes.** It hashes the project's source, test and spec files and skips
   verification when nothing changed since its last run (`.judge/hook_state.json`). A
   turn that only answers a question costs nothing.
3. **Verdict:**
   - PASS: Claude stops, and the user sees `The Judge: PASS (score ...)`.
   - FAIL / ABSTAIN: the hook returns `{"decision": "block", "reason": ...}`. The reason
     lists the next actions (`fix_code test_x: assert ...`, `add_test cache.py:45`, ...)
     and the rules (never weaken a frozen test). Claude Code hands it back to Claude,
     which keeps working.
   - Stuck (3 identical results or 5 runs without PASS, from `.judge/history.json`):
     Claude stops, and the user is told why.
4. **Never breaks the session.** Internal errors go to stderr and the exit code is
   always 0. The hook may take up to 900 s (mutation testing is part of a full verify).

The verifier is your installed `judge`, so `pip install --upgrade the-judge-verify`
updates the hook's behaviour too.

## 2. `judge improve`: review, or let an agent fix

```bash
judge improve .                     # read-only: verdict, next actions, critique
judge improve . --agent             # auto-detect a known agent (Claude Code)
judge improve . --agent "claude -p --permission-mode acceptEdits"
judge improve . --agent "aider --yes-always --message-file {prompt_file}"
```

Each round: verify, critique, then run the agent command in the workspace with a
prompt built from the verdict. The prompt goes on stdin, or into a temporary file whose
path replaces `{prompt_file}`. The judge re-verifies after the agent finishes. The loop
ends on PASS with score >= `--target-score` (default 90), after `--max-rounds` (default
5), when the agent fails (exit code != 0) or changes nothing, or after
`--agent-timeout` seconds in one round (default 1800).

Exit codes are those of `judge verify` for the final verdict: 0 PASS, 1 FAIL,
2 ABSTAIN, 3 error. A progress report is written to `_judge_report/` (`--no-report`
skips it).

Python:

```python
from the_judge import improve

result = improve(".", agent_command="claude -p --permission-mode acceptEdits", max_rounds=4)
print(result["outcome"], result["final_decision"], result["next_actions"])

# Your own repair step instead of a shell command:
def repair(workspace: str, feedback: dict) -> bool:
    ...  # read feedback["next_actions"], feedback["findings"], feedback["critique"]
    return True  # a change was made

result = improve(".", repair_func=repair)
```

A `quality_evaluator(workspace, verification_dict) -> {"score", "passed", "weaknesses"}`
adds your own bar (accessibility, UX, ...) on top of the verdict; see
[docs/API.md](docs/API.md#quality-evaluators).

## 3. Other agents

Cursor, Windsurf, Codex and Antigravity read [AGENTS.md](AGENTS.md) from the project
root; it contains the same protocol as the Claude Code skill. Agents call
`judge verify . --json` and follow `next_actions`.

## 4. Git, editor, CI

```bash
judge hook install            # pre-commit: block commits that do not PASS
judge hook install --pre-push # pre-push instead
judge init vscode             # .vscode/tasks.json: verify, contract coverage, watch
judge watch .                 # re-verify on every save
```

```yaml
# GitHub Actions
- run: pip install the-judge-verify
- run: judge verify . --json
```

## 5. Requirements: what the judge holds the code to

- **Spec rules.** List items in `TASK.md`, `SPEC.md` or `REQUIREMENTS.md` are numbered
  R1..Rn. Each needs a passing test that names its id (`def test_expiry():  # R4`).
- **`judge.json` contract.** Requirements with `id`, `description`, `priority` and
  `tests`. A requirement is verified by a passing test listed in `tests` or whose name
  contains the id. An unverified critical requirement means ABSTAIN.

```json
{
  "name": "cache-service",
  "requirements": [
    {"id": "REQ-001", "description": "Entries expire after ttl seconds",
     "priority": "critical", "tests": ["test_entry_expires_after_ttl"]}
  ]
}
```

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| ABSTAIN, `freeze_tests` | No test was fixed before the implementation changed. Write the tests, `judge freeze .`, then implement. |
| ABSTAIN, `add_test file:line` | A planted bug there went unnoticed. Add a test for that behaviour, written from the spec. |
| ABSTAIN, `cover_requirement R3` | Spec rule R3 has no passing test that names it. |
| FAIL, `restore_tests` | A frozen test was weakened or deleted. Undo that change. |
| The Stop hook does nothing | The project has no `.judge/` (run `judge freeze .`), or nothing changed since the last check. |
| `judge: command not found` in the hook | `pip install the-judge-verify` into the Python that is on Claude Code's PATH. |
