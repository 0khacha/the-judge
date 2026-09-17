# Quick Start Guide

Get started with The Judge in 5 minutes.

## Installation

```bash
pip install the-judge
```

## Basic Usage

### 1. Verify Your Code

```bash
# Verify entire workspace
judge verify .

# Verify specific file
judge verify path/to/file.py

# Get machine-readable JSON output
judge verify . --json
```

### 2. Understand the Output

```bash
judge verify .
```

**Output example:**

```
DECISION: FAIL
Score: 0.0 / 100.0

[1] [HIGH] Behavioral test failed:
    test_cache_expiration
    -> Review boundary logic in cache.py line 37.

Action: fix and re-verify.
```

### 3. Fix and Re-verify

1. Read the `suggested_focus` in the findings
2. Fix the identified issues
3. Run `judge verify .` again
4. Repeat until you get `DECISION: PASS`

### 4. Continuous Improvement

For projects that need iterative refinement:

```bash
judge improve .
```

This runs multiple rounds of evaluation and improvement until your code reaches high quality.

## Decision Types

| Decision | Meaning | Action |
|----------|---------|--------|
| **PASS** | All checks passed | Ship it! |
| **FAIL** | Issues found | Fix the findings and re-verify |
| **ABSTAIN** | Not enough evidence | Add tests or implementation |

## Integration with AI Agents

### Claude Code / Cursor / Windsurf

Add `AGENTS.md` to your project root:

```bash
curl -o AGENTS.md https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
```

The AI agent will automatically:
1. Run verification after code changes
2. Read structured findings
3. Fix issues
4. Re-verify
5. Repeat until PASS

### Manual Integration

Tell your AI assistant:

```
After every code change, run `judge verify . --json` and fix any findings before claiming the work is done.
```

## Next Steps

- Read [INSTALL.md](../INSTALL.md) for platform-specific setup
- Read [AGENTS.md](../AGENTS.md) for the agent protocol
- Read [API.md](API.md) for Python API usage
- Run `judge demo` for an interactive demo
