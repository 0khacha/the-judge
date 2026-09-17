<p align="center">
  <img src="assets/logo.svg" width="180" alt="The Judge">
</p>

<h1 align="center">The Judge</h1>

<p align="center">
  <strong>Adversarial verification & continuous improvement engine</strong>
</p>
<p align="center">
  Drive any project to high quality through evidence-based evaluation and multi-round refinement
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/0khacha/the-judge?style=flat" alt="License"></a>
  <a href="https://pypi.org/project/the-judge/"><img src="https://img.shields.io/pypi/v/the-judge?style=flat" alt="PyPI"></a>
  <a href="https://pypi.org/project/the-judge/"><img src="https://img.shields.io/pypi/pyversions/the-judge?style=flat" alt="Python"></a>
</p>

## Install

Copy/paste into your CLI prompt:

```text
Install the-judge verification plugin from https://github.com/0khacha/the-judge, refer to the repo's AGENTS.md for the verification-repair loop protocol.
```

Or install directly:

```bash
pip install the-judge
```

Check the [installation instructions](INSTALL.md) for Claude Code, Cursor, Windsurf, Codex, Git hooks, VS Code, and CI/CD.

## What it does

**The Judge** is a verification and continuous improvement engine that transforms good code into great code. It doesn't just pass/fail — it actively drives multi-round improvements until your project reaches production-quality standards.

**Core loop**: `Build → Verify → Critique → Improve → Re-verify → Repeat`

Works standalone or integrates with any AI coding assistant (Claude Code, Cursor, Windsurf, Aider, etc.) through the `AGENTS.md` protocol.

## What changes

### 1. Non-Visual Projects (Behavioral Verification)

<table>
<tr>
<td width="50%">

#### Without The Judge

> Implementation complete! All tests passed. The TTL expiration handles timestamps accurately, capacity eviction removes oldest entries, everything is ready for deployment.
>
> *(Hidden: TTL boundary check off by one. Expired keys stay valid.)*

</td>
<td width="50%">

#### With The Judge

```text
DECISION: FAIL
Score: 0.0 / 100.0

[1] [HIGH] Behavioral test failed:
    test_cache_expiration
    -> Review boundary logic in
       cache.py line 37.

Action: fix and re-verify.
```

</td>
</tr>
</table>

### 2. Visual Projects (Iterative Quality Engine)

<table>
<tr>
<td width="50%">

#### Without The Judge (Baseline Round 1)

Baseline Website - Round 1

```text
Quality Score : 52.0 / 100.0
Weaknesses    : 3 issue(s) identified
                - Browser default font
                - Basic inline CSS
                - Flat 1-column layout
```

*Basic functional implementation without visual polish, design tokens, or responsive structure.*

</td>
<td width="50%">

#### With The Judge (Plugin-Improved Round 4)

Plugin-Improved Website - Round 4

```text
Quality Score : 96.5 / 100.0 (+44.5 pts)
Weaknesses    : 0 issue(s) identified
Action Taken  : Glassmorphism, Google Fonts,
                CSS Grid, stat metrics & hover effects.
```

*Autonomous multi-round refinement engine transforms initial code into a polished, high-quality product.*

</td>
</tr>
</table>

## The rules

10 rules enforced by The Judge:

1. **Never trust self-claims.** Demand independent behavioral evidence.
2. **Execute in anonymous sandboxes.** Strip process markers and inspection flags.
3. **Synthesize challenge probes.** Prevent static test collection bypasses.
4. **Enforce requirement contracts.** Unverified critical requirements trigger ABSTAIN.
5. **Detect tampering.** Block conftest hijacking, sys.modules manipulation, TOCTOU symlinks.
6. **Track regressions.** Flag fixed bugs broken again in subsequent rounds.
7. **Return structured findings.** Actionable IDs (BEH-001), descriptions, focus areas.
8. **Predictable exit codes.** 0 = PASS, 1 = FAIL, 2 = ABSTAIN, 3 = ERROR.
9. **No false guarantees.** Verification proves evidence under tested conditions, not mathematical proof.
10. **Vendor-neutral.** Works with any agent via JSON CLI or Python API.

## Usage

```bash
judge verify .                 # Human-readable report
judge verify . --json          # Machine-readable JSON for agents
judge contract .              # Inspect requirement coverage
judge demo                    # 60-second interactive demo
```

### Plugin commands

```bash
judge hook install            # Pre-commit verification hook
judge hook install --pre-push # Pre-push verification hook
judge init vscode             # Generate VS Code tasks
judge watch .                 # Re-verify on every file save
```

### Requirement contract (judge.json)

```json
{
  "name": "cache-service",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Evict expired keys after TTL seconds elapse.",
      "category": "boundary",
      "priority": "critical",
      "properties": ["cache_expiration"]
    }
  ]
}
```

### Python API

```python
from the_judge import verify

result = verify(".", task_spec=None)
print(result.decision, result.numeric_score, result.findings)
```

### Iterative improvement API

```python
from the_judge.integrations import AgentImprovementLoop

def review_quality(workspace, verification):
    # Supply evidence from a UX, accessibility, visual, or maintainability review.
    return {
        "score": 82,
        "passed": False,
        "weaknesses": ["Keyboard focus is not visible on the primary action."],
    }

loop = AgentImprovementLoop(quality_threshold=90, quality_evaluator=review_quality)
result = loop.run_repair_loop(".", agent_repair_func=improve_from_feedback)
```

The loop gives the repair callback both Judge findings and quality weaknesses, verifies each changed round once, preserves regression evidence, and stops at the threshold or when a callback cannot make a meaningful workspace change.

## How it works

```text
Your code -> The Judge -> Sandbox execution -> Behavioral checks -> Decision
                |                                                      |
                +--- PASS: ship it                                     |
                +--- FAIL: structured findings -> agent repairs -> re-verify
                +--- ABSTAIN: insufficient evidence -> provide tests
```

The agent reads AGENTS.md, runs `judge verify . --json` after each round, parses findings, makes a concrete repair, and re-verifies. The optional `AgentRepairLoop` can also accept a quality evaluator for UX, visual quality, accessibility, or maintainability, so a passing implementation continues through meaningful improvement rounds until it reaches the configured quality bar. Maximum 5 rounds by default. No human intervention needed.

## Documentation

### Getting Started
- [Quick Start Guide](docs/QUICK_START.md) - Get started in 5 minutes
- [Installation Guide](INSTALL.md) - Platform-specific setup
- [Plugin Integration Guide](PLUGIN_GUIDE.md) - Integrate into any IDE or CLI

### Reference
- [Python API Reference](docs/API.md) - Complete API documentation
- [Agent Integration Protocol](AGENTS.md) - AI assistant integration
- [CLI Commands](docs/INDEX.md#cli-reference) - Command reference
- [Integration Examples](examples/INTEGRATION_EXAMPLES.md) - Real-world usage

### Advanced
- [Architecture Specification](docs/architecture.md) - System design
- [Development Guide](docs/DEVELOPMENT.md) - Contributing guide
- [Security Model](SECURITY.md) - Security boundaries
- [Threat Model](THREAT_MODEL.md) - Attack surface
- [Full Documentation Index](docs/INDEX.md) - All documentation

## Project Status

[![License](https://img.shields.io/github/license/0khacha/the-judge?style=flat)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/the-judge?style=flat)](https://pypi.org/project/the-judge/)
[![Python](https://img.shields.io/pypi/pyversions/the-judge?style=flat)](https://pypi.org/project/the-judge/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

**Status**: Production/Stable (v1.0.0)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/0khacha/the-judge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0khacha/the-judge/discussions)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## License

[MIT License](LICENSE) -- Copyright (c) 2026 **@0khacha**
