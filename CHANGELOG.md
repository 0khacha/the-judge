# Changelog

All notable changes to The Judge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-31

### Added
- **Claude Code plugin** (`plugin/`, marketplace `.claude-plugin/marketplace.json`):
  `/plugin install the-judge --marketplace 0khacha/the-judge`. It adds a Stop hook, the
  `judge-loop` skill (the test-first protocol) and `/the-judge:verify`,
  `/the-judge:freeze` and `/the-judge:improve`.
- **Stop hook** (`judge hook run`, `python -m the_judge.hook`). At the end of a turn it
  verifies the project if source/test/spec files changed since its last run. Unless the
  verdict is PASS, it returns `{"decision": "block", "reason": <next actions>}`, so
  Claude keeps fixing. It is opt-in per project (`.judge/` exists;
  `THE_JUDGE_HOOK=always|off`), and it lets Claude stop when the judge reports the loop
  as stuck.
- **`judge improve --agent [CMD]`** / `improve(agent_command=...)`: each round a coding
  agent (default: Claude Code, `claude -p`) gets the verdict's next actions as its
  prompt, on stdin or via `{prompt_file}`, and the judge re-verifies after it finishes.
  Ends on PASS, `--max-rounds`, an agent failure, or a round without changes
  (`--agent-timeout`, default 1800 s).
- `judge improve` prints the judge's next actions, loads `judge.json` like `verify`
  (`--task-spec`), and exits with the verdict's code (0 PASS, 1 FAIL, 2 ABSTAIN). The
  result dict has `next_actions`.
- `examples/simple_cache` is a working walk-through: SPEC.md rules R1-R5, tests naming
  them, a stub, a correct solution (PASS) and an off-by-one one (FAIL). CI runs it.

### Changed
- **Python 3.10 or newer is required.** Python 3.9 reached end of life in October 2025
  and is no longer available on CI runners, so support could not be tested.
- **`judge improve` is read-only by default.** Without `--agent` or a repair callback
  it runs one evaluation round, changes no files, and returns outcome `REVIEW_ONLY` with
  `next_actions` and the critique in `suggestions`.
- The PostToolUse hook that ran a full verification after any Bash command containing
  `python`/`make`/... is replaced by the Stop hook. On FAIL it exited 1, which Claude
  Code shows only to the user, so the agent never saw the findings.
- The checklist drops a rule's own label from its text (`- R4: ...` is no longer shown
  as `R4 (SPEC.md): R4: ...`).
- The critique no longer claims "no boundary tests" when mutation testing showed that
  the planted boundary bugs were caught.
- The version is defined once (`the_judge/_version.py`); CLI, reports and JSON output
  (`judge_version`) read it from there. Some outputs previously said `v4.0`.

### Removed
- **`AutoImprover`, `judge improve --apply`, `improve(apply=True)`.** It inserted
  `if any(p is None ...): raise ValueError` guards into arbitrary functions, stamped
  "Auto-improved by The Judge" docstrings, marked syntax errors with a comment, and
  created a `judge.json` whose critical requirement no test could satisfy (a permanent
  ABSTAIN). It could not fix behaviour. `--apply` now exits 3 and `apply=True` raises
  `ValueError`, both pointing to `--agent`.
- Dead code: `BehaviorEngine` (it had returned no probes since the generic probes were
  removed), `ContractParser`, `parse_pytest_output`,
  `SandboxRunner.execute_fresh_process_probe`, `CritiqueResult.get_open_by_severity`, the
  legacy `judge` import shim, `setup.py`, the quick-start scripts.
- The simulated agent benchmark (`benchmark/`), superseded by the pre-registered
  evaluations in `eval_results/`; the duplicated `docs/security.md` and
  `docs/threat-model.md` (stale "v4.0" copies of SECURITY.md / THREAT_MODEL.md); unused
  `assets/`; `examples/alex_morgan_portfolio/run_improvement_experiment.py`, which printed
  hard-coded scores as an experiment; the duplicate `tests.yml` workflow.
- PLUGIN_GUIDE.md no longer documents settings that never existed (`~/.judge/config.json`,
  `exclude_patterns`, `quality_threshold` in judge.json).

### Fixed
- docs/API.md and examples/INTEGRATION_EXAMPLES.md showed repair callbacks returning
  `{"changed": True}`; the loop reads `"improved"`, so they aborted after one round. The
  examples also read result keys that do not exist (`final_score`, `rounds`,
  `feedback["verification"]`).
- The CI "self-verify" job ran `judge verify .` on an unchanged checkout, which is
  always ABSTAIN (exit 2); it is replaced by the walk-through job.
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
