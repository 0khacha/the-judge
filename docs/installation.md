# How to install

> **Install `the-judge-verify`.** The PyPI project named `the-judge` is an
> **unrelated package** by another author:
> `pip install the-judge-verify`

mypy and ruff are **optional**. If they are on `PATH`, The Judge also runs them; if not,
those checks are skipped and reported as a `tooling` finding with reduced confidence,
and the decision is unaffected. To enable them: `pip install mypy ruff`.

<details>
<summary><strong>pip (universal)</strong></summary>

### Install

```bash
pip install the-judge-verify
```

### Verify

```bash
judge --version
judge verify .
```

### Update

```bash
pip install --upgrade the-judge-verify
```

### Uninstall

```bash
pip uninstall the-judge-verify
```

</details>

<details>
<summary><strong>Claude Code</strong></summary>

### Install (plugin)

```bash
pip install the-judge-verify
```

Then, in Claude Code:

```text
/plugin install the-judge --marketplace 0khacha/the-judge
```

(Before Claude Code 2.1.275: `/plugin marketplace add 0khacha/the-judge`, then
`/plugin install the-judge@the-judge`.)

The plugin adds:

- **A Stop hook.** When Claude finishes a turn in a project that uses The Judge (it has
  a `.judge/` folder, created by `judge freeze`) and the code changed since the last
  check, the judge verifies it. Unless the verdict is PASS, the turn is sent back to
  Claude with the judge's numbered next actions, so it keeps fixing until PASS. It stops
  when nothing changed or the judge reports the loop as stuck. Projects without
  `.judge/` are never touched; `THE_JUDGE_HOOK=always` / `off` overrides this.
- **The `judge-loop` skill.** It teaches Claude the protocol: tests first, freeze,
  implement, verify, follow `next_actions`.
- **Commands:** `/the-judge:verify`, `/the-judge:freeze`, `/the-judge:improve`.

### Use

Ask Claude to implement something "test-first with the judge", or run
`/the-judge:freeze` after the tests are written. From then on every turn that changes
code ends with a verification.

### Without the plugin

Copy/paste into your Claude Code prompt:

```text
Run `pip install the-judge-verify` to install the verification tool, then read
AGENTS.md at https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
for the verification-repair loop protocol. After every critical code change,
run `judge verify . --json` and act on the findings.
```

Or add the hook to a project by hand, in `.claude/settings.json`:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "judge hook run", "timeout": 900}]}]}}
```

</details>

<details>
<summary><strong>Cursor</strong></summary>

### Install

1. Install the package: `pip install the-judge-verify`
2. Copy `AGENTS.md` to your project root:

```bash
curl -o AGENTS.md https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
```

Cursor reads `AGENTS.md` and auto-applies the verification loop.

### Verify

Ask Cursor to run `judge verify .` after each code change.

### VS Code Tasks

```bash
judge init vscode
```

Then `Ctrl+Shift+P` -> `Tasks: Run Task` -> `Judge: Verify Workspace`.

</details>

<details>
<summary><strong>Windsurf</strong></summary>

### Install

1. Install the package: `pip install the-judge-verify`
2. Add `AGENTS.md` to your project root.

Windsurf reads `AGENTS.md` and follows the verification-repair loop automatically.

### Verify

```bash
judge verify .
```

</details>

<details>
<summary><strong>Codex</strong></summary>

### Install

1. Install the package: `pip install the-judge-verify`
2. Add `AGENTS.md` to your project root or `~/.codex/AGENTS.md` for global use.

### Verify

```bash
judge verify . --json
```

Codex parses JSON output and uses `findings[].suggested_focus` for repairs.

</details>

<details>
<summary><strong>Antigravity (<code>agy</code>)</strong></summary>

### Install

```bash
pip install the-judge-verify
```

Add `AGENTS.md` to your project root. Antigravity auto-discovers it.

### Verify

```bash
judge verify . --json
```

### Always-on

Add to `~/.gemini/GEMINI.md`:

```markdown
## Verification

After every code change, run `judge verify . --json`. If decision is FAIL, read findings[].suggested_focus, fix the code, and re-verify. Never claim code works without PASS.
```

</details>

<details>
<summary><strong>Git hooks</strong></summary>

### Install

```bash
judge hook install            # pre-commit hook
judge hook install --pre-push # pre-push hook
```

Blocks commits/pushes that fail verification.

### Uninstall

```bash
judge hook uninstall
judge hook uninstall --pre-push
```

</details>

<details>
<summary><strong>VS Code</strong></summary>

### Install

```bash
judge init vscode
```

Creates `.vscode/tasks.json` with:
- **Judge: Verify Workspace** -- run verification from Command Palette
- **Judge: Contract Coverage** -- inspect requirement coverage
- **Judge: Watch Mode** -- continuous verification on file save

### Use

`Ctrl+Shift+P` -> `Tasks: Run Task` -> pick a Judge task.

</details>

<details>
<summary><strong>Watch mode (any editor)</strong></summary>

### Run

```bash
judge watch .
```

Watches `.py` files. Re-verifies automatically on save. Works with any editor.

### Options

```bash
judge watch . --debounce 3    # 3-second debounce (default: 2)
```

### Stop

`Ctrl+C`.

</details>

<details>
<summary><strong>Python API</strong></summary>

### Install

```bash
pip install the-judge-verify
```

### Use

```python
from the_judge import verify

result = verify(".", task_spec=None)
print(result.decision)        # PASS, FAIL, or ABSTAIN
print(result.numeric_score)   # 0.0 - 100.0
print(result.findings)        # Structured findings list
```

### Agent adapter

```python
from the_judge.integrations.agent_adapter import AgentAdapter

adapter = AgentAdapter(name="MyAgent")
feedback = adapter.verify_workspace(".")
prompt = adapter.format_agent_prompt_feedback(feedback)
```

### Repair loop

```python
from the_judge import improve

# Let a coding agent fix what the judge finds, re-verifying after each round.
result = improve(".", agent_command="claude -p --permission-mode acceptEdits")

# Or your own callback: (workspace, feedback) -> bool
result = improve(".", repair_func=my_repair_fn)
```

</details>

<details>
<summary><strong>CI/CD (GitHub Actions)</strong></summary>

### Add to workflow

```yaml
- name: Install The Judge
  run: pip install the-judge-verify

- name: Verify
  run: judge verify . --json
```

Exit code `0` = PASS, `1` = FAIL, `2` = ABSTAIN, `3` = ERROR.

</details>
