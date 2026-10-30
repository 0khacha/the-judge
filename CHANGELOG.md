# Changelog

All notable changes to The Judge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **`judge improve` is read-only by default.** Without a repair callback it runs one
  evaluation round, changes no files, and returns outcome `REVIEW_ONLY` with the open
  critique findings in `suggestions`. `judge improve --apply` / `improve(apply=True)`
  lets the built-in `AutoImprover` edit files as before.
- The version is defined once (`the_judge/_version.py`); CLI, reports and JSON output
  (`judge_version`) read it from there. Some outputs previously said `v4.0`.

### Removed
- `AutoImprover` no longer writes tests. The tests it generated (`assert callable(f)`,
  `assert True`, `pytest.raises` around a bare `raise`) passed regardless of the code
  and were counted as independent evidence.

### Fixed
- False FAIL with "COLLECTION TAMPERING DETECTED" / `restore_tests` on correct,
  untouched projects, from three causes:
  - tests reading fixtures through `__file__` (e.g. `tests/data/sample.csv`) failed to
    import in the sandbox: files under the test directories and the project's other
    non-Python files are now copied there (directories in `norecursedirs` are copied
    but, as in the workspace, not collected);
  - suites slower than the fixed 30 s sandbox limit: the limit is now 300 s and
    configurable (`judge verify --timeout N`, `verify(timeout=N)`), and a run stopped
    at the limit is ABSTAIN with a `raise_timeout` action instead of tampering;
  - the git-baseline check compared every tracked `test_*.py`, so test files outside
    `testpaths` or under `norecursedirs` were reported as removed tests.
- The git-baseline check decoded `git show` output in the locale code page, so a
  committed test with non-ASCII text in an assertion was reported as "lost
  assertion(s)" on Windows.
- Sandboxed test output with bytes the locale code page cannot decode no longer loses
  the captured output.
- The PostToolUse hook (`judge hook run`, `python -m the_judge.hook`) crashed on every
  FAIL verdict (`'Finding' object has no attribute 'get'`) and exited 0, so FAIL was
  never reported to the agent.
- CLI and hook output no longer crash with `UnicodeEncodeError` when stdout is a pipe on
  a non-UTF-8 code page (Windows) and the report contains text such as `→` or CJK from
  a failing test's message; output is written as UTF-8.
- JUnit `<testcase>` entries without a name are ignored instead of recorded as `None`.
- Unclosed file handles in the critique engine and improver; `ruff check` and `mypy`
  are clean.

## [1.0.2] - 2026-10-29

### Added
- Requirements checklist: each rule of `TASK.md` / `SPEC.md` / `REQUIREMENTS.md`
  (R1..Rn) needs a passing test that names it.
- Mutation feedback: before PASS, small bugs are planted in the implementation;
  uncaught ones become `add_test file.py:LINE` actions.

### Fixed
- A re-freeze no longer erases earlier independent evidence.
- Helper, fixture and non-`assert` tests are no longer reported as vacuous.

## [1.0.1] - 2026-10-28

### Added
- Iteration history (`.judge/history.json`), explicit regressions and a clean stop
  when stuck.

### Fixed
- Parametrized tests are not collection tampering.
- "No tests collected" is ABSTAIN with what is missing, not FAIL.
- Static analysis (mypy/ruff) is advisory and never decides correctness.
- Detection of outcome-rewriting hooks and hard-coded expected outputs.

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
