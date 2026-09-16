# How to install

<details>
<summary><strong>pip (universal)</strong></summary>

### Install

```bash
pip install the-judge
```

### Verify

```bash
judge --version
judge verify .
```

### Update

```bash
pip install --upgrade the-judge
```

### Uninstall

```bash
pip uninstall the-judge
```

</details>

<details>
<summary><strong>Claude Code</strong></summary>

### Install

Copy/paste into your Claude Code prompt:

```text
Install the-judge verification plugin from https://github.com/0khacha/the-judge. Read the AGENTS.md for the verification-repair loop protocol. After every critical code change, run `judge verify . --json` and act on the findings.
```

Or add the `AGENTS.md` to your project root:

```bash
curl -o AGENTS.md https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
```

Claude Code auto-discovers `AGENTS.md` and follows the verification protocol.

### Verify

Ask Claude Code to run `judge verify .` and check for structured findings.

### Always-on

Add to your project's `AGENTS.md` or `~/.claude/CLAUDE.md`:

```markdown
## Verification

After every code change, run `judge verify . --json`. If FAIL, fix the findings and re-verify. Never claim code works without a PASS from The Judge.
```

</details>

<details>
<summary><strong>Cursor</strong></summary>

### Install

1. Install the package: `pip install the-judge`
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

1. Install the package: `pip install the-judge`
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

1. Install the package: `pip install the-judge`
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
pip install the-judge
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
pip install the-judge
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
from the_judge.integrations.repair_loop import AgentRepairLoop

loop = AgentRepairLoop(max_rounds=5)
result = loop.run_repair_loop(".", agent_repair_func=my_repair_fn)
```

</details>

<details>
<summary><strong>CI/CD (GitHub Actions)</strong></summary>

### Add to workflow

```yaml
- name: Install The Judge
  run: pip install the-judge

- name: Verify
  run: judge verify . --json
```

Exit code `0` = PASS, `1` = FAIL, `2` = ABSTAIN, `3` = ERROR.

</details>
