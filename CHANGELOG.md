# Changelog

All notable changes to The Judge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-17

### Added
- **Core Verification Engine**: Evidence-based code verification with sandbox execution
- **Critique Engine**: Adversarial critique system for identifying weaknesses and assumptions
- **Continuous Improvement Loop**: Multi-round autonomous refinement until quality threshold
- **Visual Evaluation**: Automatic detection and evaluation of visual projects (web, UI, dashboards)
- **Behavioral Verification**: Non-visual project evaluation via test suites and contracts
- **CLI Interface**: Complete command-line tool (`judge` command)
- **Python API**: Programmatic access via `verify()`, `improve()`, `critique()`
- **Agent Integration**: Protocol for AI coding assistants (Claude Code, Cursor, Windsurf)
- **Git Hooks**: Pre-commit and pre-push verification hooks
- **IDE Integration**: VS Code tasks, file watcher mode
- **Requirement Contracts**: `judge.json` specification for critical requirements
- **Audit Trail**: Complete tracking of improvement rounds and changes
- **Progress Reports**: Detailed reporting of verification and improvement progress

### Core Features
- Sandbox execution with anonymous process isolation
- Dynamic property checks and challenge probes
- Tampering detection (conftest hijacking, sys.modules manipulation)
- Regression tracking across rounds
- Structured findings with actionable guidance
- Exit codes: 0=PASS, 1=FAIL, 2=ABSTAIN, 3=ERROR
- JSON output format for machine consumption

### Documentation
- Comprehensive README with visual examples
- Installation guide for multiple platforms and tools
- Agent integration protocol (AGENTS.md)
- Security model and threat boundaries
- API reference documentation
- Quick start guide
- Development guide
- Integration examples

### Project Structure
- Professional Python package structure
- Type hints and py.typed marker
- Ruff + mypy for code quality
- pytest test suite
- Makefile for common tasks
- VS Code configuration
- GitHub issue templates

[1.0.0]: https://github.com/0khacha/the-judge/releases/tag/v1.0.0
