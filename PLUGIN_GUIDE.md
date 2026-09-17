# The Judge - Plugin Integration Guide

This guide shows how to integrate The Judge as a plugin into any IDE or CLI workflow.

## Overview

The Judge is designed to be easily integrated into any development environment through:

1. **CLI Interface** - Simple command-line tool
2. **Python API** - Programmatic access
3. **Git Hooks** - Automatic verification
4. **IDE Tasks** - Editor integration
5. **CI/CD** - Continuous integration
6. **Agent Protocol** - AI assistant integration

## Core Philosophy

**The Judge improves any project to high quality through:**

- **Continuous evaluation** - Not just pass/fail, but iterative improvement
- **Evidence-based verification** - Demands behavioral proof, not claims
- **Adversarial critique** - Identifies weaknesses and assumptions
- **Multi-round refinement** - Keeps improving until quality threshold is met

## Quick Integration

### 1. As a CLI Plugin

```bash
# Install
pip install the-judge

# Use in any project
cd /path/to/your/project
judge verify .

# Continuous improvement mode
judge improve .
```

### 2. As a Python Library

```python
from the_judge import verify, improve

# Simple verification
result = verify(".")
print(result.decision, result.numeric_score)

# Continuous improvement
result = improve(".", target_score=90.0, max_rounds=5)
```

### 3. With AI Agents (Claude Code, Cursor, Windsurf)

Add `AGENTS.md` to your project:

```bash
curl -o AGENTS.md https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
```

The AI agent will automatically:
- Run verification after code changes
- Parse findings
- Fix issues
- Re-verify
- Repeat until PASS

### 4. As a Git Hook

```bash
# Pre-commit hook (blocks bad commits)
judge hook install

# Pre-push hook (blocks bad pushes)
judge hook install --pre-push
```

### 5. In VS Code / Cursor

```bash
# Generate tasks
judge init vscode

# Use: Ctrl+Shift+P -> Tasks: Run Task -> Judge: Verify Workspace
```

### 6. In CI/CD

```yaml
# GitHub Actions
- name: Install The Judge
  run: pip install the-judge

- name: Verify Code Quality
  run: judge verify . --json
```

## Integration Features

### CLI Commands

```bash
judge verify .                 # Verify workspace
judge verify . --json          # Machine-readable output
judge improve .                # Continuous improvement mode
judge contract .              # Show requirement coverage
judge watch .                 # Auto-verify on file changes
judge demo                    # Interactive demo
judge hook install            # Install git hook
judge init vscode             # Generate IDE tasks
```

### Exit Codes

- `0` = PASS - All checks passed
- `1` = FAIL - Issues detected
- `2` = ABSTAIN - Insufficient evidence
- `3` = ERROR - Execution error

### JSON Output Format

```json
{
  "decision": "FAIL",
  "numeric_score": 65.0,
  "findings": [
    {
      "id": "BEH-001",
      "category": "behavior",
      "severity": "high",
      "description": "Test failed: test_cache_expiration",
      "suggested_focus": "Review boundary logic in cache.py:37"
    }
  ],
  "trust_profile": {
    "evidence_level": 3,
    "total_tests": 10,
    "passed_tests": 8,
    "failed_tests": 2
  },
  "provenance": {
    "workspace_hash": "a1b2c3...",
    "judge_version": "v1.0.0",
    "timestamp": "2026-09-17T12:00:00Z"
  }
}
```

### Python API

```python
from the_judge import verify, improve, critique

# Basic verification
result = verify(".", task_spec=None)

# With requirement contract
import json
with open("judge.json") as f:
    contract = json.load(f)
result = verify(".", task_spec=contract)

# Continuous improvement
result = improve(
    workspace=".",
    target_score=90.0,
    max_rounds=5
)

# Adversarial critique
critique_result = critique(".")
```

### Custom Quality Evaluators

```python
from the_judge import improve

def my_quality_evaluator(workspace, verification):
    """Custom domain-specific quality checks."""
    score = 70
    weaknesses = []
    
    # Your custom checks
    if not meets_accessibility_standards():
        weaknesses.append("Accessibility issues")
        score -= 20
    
    if not has_proper_documentation():
        weaknesses.append("Documentation incomplete")
        score -= 10
    
    return {
        "score": score,
        "passed": score >= 90,
        "weaknesses": weaknesses
    }

result = improve(
    workspace=".",
    quality_evaluator=my_quality_evaluator,
    target_score=95.0
)
```

## IDE Integration Patterns

### Pattern 1: Manual Trigger

User manually runs verification when needed.

**VS Code:**
- Add task in `.vscode/tasks.json`
- Run via Command Palette

**JetBrains:**
- Add External Tool
- Assign keyboard shortcut

### Pattern 2: File Watcher

Automatic verification on file save.

```bash
judge watch .
```

Or IDE-specific file watchers.

### Pattern 3: Pre-commit Hook

Verification runs before every commit.

```bash
judge hook install
```

### Pattern 4: AI Agent Integration

Agent reads `AGENTS.md` and follows protocol automatically.

## Project Type Adaptability

The Judge automatically adapts to your project type:

### Visual Projects (Web, UI, Dashboards)
- Captures screenshots
- Evaluates visual quality
- Checks typography, spacing, layout
- Multi-round visual refinement

### Non-Visual Projects (Libraries, APIs, CLI)
- Runs test suites
- Checks behavioral properties
- Verifies contracts
- Analyzes structure

## Best Practices

### 1. Start Simple

```bash
judge verify .
```

### 2. Add Requirement Contracts

Create `judge.json` for critical requirements:

```json
{
  "name": "my-project",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Must handle edge case X",
      "category": "boundary",
      "priority": "critical"
    }
  ]
}
```

### 3. Use Continuous Improvement

```bash
judge improve .
```

Runs multiple rounds until high quality is achieved.

### 4. Integrate with CI/CD

Ensure code quality in your pipeline:

```yaml
- run: judge verify . --json
```

### 5. Enable for AI Agents

Let AI assistants auto-verify their work:

```bash
curl -o AGENTS.md https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
```

## Configuration

### Per-project Configuration

`judge.json` in project root:

```json
{
  "name": "my-project",
  "requirements": [...],
  "exclude_patterns": ["**/node_modules/**", "**/.venv/**"],
  "quality_threshold": 90.0
}
```

### Global Configuration

`~/.judge/config.json`:

```json
{
  "default_quality_threshold": 90.0,
  "max_rounds": 5,
  "auto_install_hooks": false
}
```

## Troubleshooting

### No Tests Found

```bash
# Make sure you have test files
ls test_*.py

# Or provide task_spec
judge verify . --task-spec judge.json
```

### ABSTAIN Decision

Add more tests to provide behavioral evidence:

```python
def test_my_feature():
    assert my_function() == expected_result
```

### Low Score

Use improvement mode:

```bash
judge improve .
```

## See Also

- [INSTALL.md](../INSTALL.md) - Installation guide
- [API.md](../docs/API.md) - Python API reference
- [AGENTS.md](../AGENTS.md) - Agent protocol
- [examples/](../examples/) - Integration examples

## Support

- **Issues**: https://github.com/0khacha/the-judge/issues
- **Discussions**: https://github.com/0khacha/the-judge/discussions
- **Documentation**: https://github.com/0khacha/the-judge#readme
