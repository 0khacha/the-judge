# Documentation Index

Complete documentation for The Judge verification and improvement engine.

## Getting Started

- **[README](../README.md)** - Project overview and quick introduction
- **[Quick Start Guide](QUICK_START.md)** - Get started in 5 minutes
- **[Installation Guide](../INSTALL.md)** - Platform-specific installation instructions
- **[Plugin Integration Guide](../PLUGIN_GUIDE.md)** - Integrate into any IDE or CLI

## Core Documentation

- **[Python API Reference](API.md)** - Complete API documentation
- **[Agent Integration Protocol](../AGENTS.md)** - Protocol for AI coding assistants
- **[Architecture Specification](architecture.md)** - System design and components
- **[Security Model](../SECURITY.md)** - Security boundaries and guarantees
- **[Threat Model](../THREAT_MODEL.md)** - Adversarial attack surface

## Guides

- **[Development Guide](DEVELOPMENT.md)** - Contributing and development setup
- **[Integration Examples](../examples/INTEGRATION_EXAMPLES.md)** - Real-world usage patterns
- **[Changelog](../CHANGELOG.md)** - Version history and changes

## Examples

- **[Simple Cache](../examples/simple_cache/)** - Basic verification example
- **[Visual Projects](../examples/)** - Web UI improvement examples
- **[Custom Evaluators](../examples/INTEGRATION_EXAMPLES.md#example-7-visual-project-evaluation)** - Domain-specific quality checks

## Reference

- **[CLI Commands](#cli-reference)** - Command-line interface reference
- **[Exit Codes](#exit-codes)** - Return value meanings
- **[JSON Output Format](#json-format)** - Machine-readable output specification
- **[Requirement Contracts](#contract-specification)** - judge.json format

---

## CLI Reference

### Verification Commands

```bash
judge verify .                 # Verify workspace (human-readable)
judge verify . --json          # Verify workspace (JSON output)
judge verify path/to/file.py   # Verify specific file
judge contract .              # Show requirement coverage
```

### Improvement Commands

```bash
judge improve .                # Continuous improvement mode
judge improve . --rounds 10    # Custom max rounds
judge improve . --score 95     # Custom target score
```

### Integration Commands

```bash
judge hook install             # Install pre-commit hook
judge hook install --pre-push  # Install pre-push hook
judge hook uninstall           # Remove hooks
judge init vscode              # Generate VS Code tasks
judge watch .                  # Watch mode (auto-verify on save)
judge watch . --debounce 3     # Custom debounce interval
```

### Utility Commands

```bash
judge demo                     # Interactive 60-second demo
judge --version                # Show version
judge --help                   # Show help
```

---

## Exit Codes

| Code | Decision | Meaning | Action |
|------|----------|---------|--------|
| 0 | PASS | All checks passed | Ship it |
| 1 | FAIL | Issues detected | Fix and re-verify |
| 2 | ABSTAIN | Insufficient evidence | Add tests |
| 3 | ERROR | Execution error | Check workspace path |

---

## JSON Format

### Verification Result

```json
{
  "decision": "PASS" | "FAIL" | "ABSTAIN",
  "numeric_score": 0.0 to 100.0,
  "findings": [
    {
      "id": "BEH-001",
      "category": "behavior" | "security" | "type_check" | "regression",
      "severity": "low" | "medium" | "high" | "blocking",
      "description": "Human-readable description",
      "property_name": "test_name",
      "observed": "What was observed",
      "expected": "What was expected",
      "suggested_focus": "Actionable guidance"
    }
  ],
  "trust_profile": {
    "evidence_level": 0 to 5,
    "total_tests": 10,
    "passed_tests": 8,
    "failed_tests": 2,
    "specification_coverage": { ... }
  },
  "provenance": {
    "workspace_path": "/path/to/workspace",
    "workspace_hash": "sha256...",
    "judge_version": "v1.0.0",
    "timestamp": "2026-09-17T12:00:00Z"
  },
  "blocking_issues": [ "Issue descriptions" ],
  "insufficient_notes": [ "Evidence gap descriptions" ],
  "runtime_seconds": 1.234
}
```

### Improvement Result

```json
{
  "final_decision": "PASS",
  "final_score": 95.5,
  "rounds": [
    {
      "round": 1,
      "score": 65.0,
      "decision": "FAIL",
      "findings_count": 3,
      "changes": "Fixed cache expiration bug"
    },
    {
      "round": 2,
      "score": 85.0,
      "decision": "PASS",
      "findings_count": 0,
      "changes": "Added thread safety"
    }
  ],
  "score_progression": [65.0, 85.0, 95.5],
  "total_rounds": 3,
  "improvements_made": true
}
```

---

## Contract Specification

### judge.json Format

```json
{
  "name": "project-name",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Human-readable requirement",
      "category": "boundary" | "behavior" | "security" | "performance",
      "priority": "critical" | "high" | "medium" | "low",
      "properties": ["test_name_1", "test_name_2"]
    }
  ],
  "exclude_patterns": ["**/node_modules/**", "**/.venv/**"],
  "quality_threshold": 90.0
}
```

### Requirement Categories

- **boundary** - Edge cases, limits, boundaries
- **behavior** - Core functionality and logic
- **security** - Security requirements
- **performance** - Performance requirements
- **concurrency** - Thread safety, race conditions

### Priority Levels

- **critical** - Must pass for PASS decision
- **high** - Important, but can defer
- **medium** - Should have
- **low** - Nice to have

---

## Finding Categories

| Category | Description | Severity Range |
|----------|-------------|----------------|
| **behavior** | Test failures, logic errors | high, blocking |
| **security** | Security issues, tampering | blocking |
| **type_check** | Type errors from mypy | high |
| **regression** | Previously fixed bugs returning | blocking |
| **collection** | Insufficient evidence | medium |

---

## Evidence Levels

| Level | Description |
|-------|-------------|
| 0 | No evidence |
| 1 | Implementation only, no tests |
| 2 | Basic tests present |
| 3 | Good test coverage |
| 4 | Comprehensive tests + property checks |
| 5 | Adversarial tests + regression tracking |

---

## Comparison with Other Tools

| Feature | The Judge | pytest | mypy | SonarQube |
|---------|-----------|--------|------|-----------|
| Test execution | ✓ | ✓ | ✗ | ✓ |
| Type checking | ✓ | ✗ | ✓ | ✗ |
| Continuous improvement | ✓ | ✗ | ✗ | ✗ |
| Adversarial critique | ✓ | ✗ | ✗ | ✗ |
| AI agent integration | ✓ | ✗ | ✗ | ✗ |
| Visual evaluation | ✓ | ✗ | ✗ | ✗ |
| Requirement contracts | ✓ | ✗ | ✗ | ✓ |
| Multi-round refinement | ✓ | ✗ | ✗ | ✗ |

**The Judge is complementary** - it uses pytest, mypy, and other tools internally, but adds continuous improvement and adversarial verification on top.

---

## Support

- **Issues**: https://github.com/0khacha/the-judge/issues
- **Discussions**: https://github.com/0khacha/the-judge/discussions
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## License

[MIT License](../LICENSE) - Copyright (c) 2026 @0khacha
