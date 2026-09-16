# Universal Integration Guide: The Judge v1.0.0

`the_judge` provides a vendor-neutral CLI, machine-readable JSON interface, and Python API for integrating into AI agent execution loops, IDE editors, CI/CD pipelines, and git hooks.

---

## 1. Vendor-Neutral AI Agent Integration Protocol

AI coding agents (OpenAI, Anthropic, Cursor, Claude Code, custom agents) can invoke The Judge CLI to obtain structured verification findings:

```bash
judge verify <workspace> --json
```

### Response Schema Protocol

```json
{
  "decision": "PASS", // "PASS", "FAIL", "ABSTAIN", or "ERROR"
  "numeric_score": 90.0,
  "findings": [
    {
      "id": "BEH-001",
      "category": "behavior",
      "severity": "high",
      "description": "Behavioral test failed: test_prop_expiration_cache_LRUCache",
      "observed": "Behavioral test execution failed.",
      "expected": "Test passes with return value matching observable spec.",
      "suggested_focus": "Review state transitions and boundary logic."
    }
  ],
  "blocking_issues": [],
  "insufficient_notes": []
}
```

### Agent State Transition Rule

- **PASS (`exit code 0`)**: Accept implementation and commit workspace changes.
- **FAIL (`exit code 1`)**: Parse `findings` array and feed structured items into agent LLM repair prompt.
- **ABSTAIN (`exit code 2`)**: Generate additional property challenge tests or request clarification in `judge.json`.
- **ERROR (`exit code 3`)**: Fix syntax error or workspace environment configuration issue.

---

## 2. Generic IDE & Editor Integration Pattern

The Judge does not require proprietary, vendor-specific IDE plugins. Editors can invoke the CLI in any directory and map JSON findings into editor diagnostics.

```text
Editor / IDE (VS Code, Cursor, JetBrains, Neovim, Emacs)
      │
      └── Invokes: judge verify . --json
               │
               └── Parses: findings[]
                        │
                        └── Displays: In-editor inline diagnostics
```

### Example VS Code Task Configuration (`.vscode/tasks.json`)

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "The Judge: Verify Workspace",
      "type": "shell",
      "command": "judge verify . --json",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared"
      }
    }
  ]
}
```

---

## 3. CI/CD Integration (GitHub Actions)

The Judge CLI exit codes allow effortless integration as a mandatory release quality gate in continuous integration pipelines:

```yaml
name: Continuous Verification Gate

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install The Judge
        run: pip install the-judge

      - name: Execute Verification Gate
        run: judge verify . --json
```

---

## 4. Programmatic Python API

```python
from the_judge import verify

# Verify workspace code
result = verify(workspace=".", task_spec=None)

print(f"Decision: {result.decision}")
print(f"Numeric Score: {result.numeric_score}/100.0")

if result.decision == "FAIL":
    for finding in result.findings:
        print(f"[{finding.severity}] {finding.description}")
        print(f"  Suggested Focus: {finding.suggested_focus}")
```

### Multi-Round Agent Repair Loop

```python
from the_judge.integrations.agent_adapter import AgentAdapter
from the_judge.integrations.repair_loop import AgentRepairLoop

adapter = AgentAdapter()
repair_loop = AgentRepairLoop(adapter=adapter, max_rounds=4)

def agent_repair_callback(workspace_dir: str, feedback: dict) -> bool:
    # 1. Pass feedback['findings'] to LLM agent prompt
    # 2. LLM agent modifies target files in workspace_dir
    # 3. Return True to continue loop, False to abort
    return True

outcome = repair_loop.run_repair_loop(".", agent_repair_callback)
print("Final Repair Outcome:", outcome["outcome"])
```
