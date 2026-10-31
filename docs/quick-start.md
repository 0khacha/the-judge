# Quick Start Guide

Get started with The Judge in 5 minutes.

## Installation

> **Install `the-judge-verify`.** The PyPI project named `the-judge` is an
> **unrelated package** by another author:
> `pip install the-judge-verify`

```bash
pip install the-judge-verify
```

mypy and ruff are **optional**. If they are on `PATH`, The Judge also runs them; if not,
those checks are skipped and reported as a `tooling` finding with reduced confidence,
and the decision is unaffected. To enable them: `pip install mypy ruff`.

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

### 4. Let an agent do the fixing

```bash
judge improve .                     # read-only review: verdict, next actions, critique
judge improve . --agent             # a coding agent (Claude Code) fixes, the judge re-verifies
```

Without `--agent` nothing is changed. With it, each round the agent gets the judge's
next actions as its prompt, then the judge verifies independently, until PASS or
`--max-rounds`. A walk-through: [examples/simple_cache](../examples/simple_cache/README.md).

## Decision Types

| Decision | Meaning | Action |
|----------|---------|--------|
| **PASS** | All checks passed | Ship it! |
| **FAIL** | Issues found | Fix the findings and re-verify |
| **ABSTAIN** | Not enough evidence | Add tests or implementation |

## Integration with AI Agents

### Claude Code

Install the plugin (`/plugin install the-judge --marketplace 0khacha/the-judge`): its Stop
hook verifies every turn that changed code and sends the work back until PASS. See
[claude-code-plugin.md](claude-code-plugin.md).

### Cursor / Windsurf / Codex

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

- Read [installation.md](installation.md) for platform-specific setup
- Read [AGENTS.md](../AGENTS.md) for the agent protocol
- Read [python-api.md](python-api.md) for Python API usage
- Run `judge demo` for an interactive demo
