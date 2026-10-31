# Contributing

Bug reports, fixes and new integrations are welcome. For anything larger than a fix,
open an [issue](https://github.com/0khacha/the-judge/issues) first so the approach can
be agreed before you write it.

## Setup

```bash
git clone https://github.com/0khacha/the-judge.git
cd the-judge
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # Python 3.10+
```

| Command | What it runs |
|---|---|
| `make test` | `pytest tests/` (about 5-10 minutes: many tests run the judge end to end) |
| `make lint` | `ruff check` and `mypy` |
| `make format` | `ruff format` and autofixes |
| `make plugin` | `claude plugin validate` for the marketplace and the plugin (needs the `claude` CLI) |

CI runs lint and tests on Ubuntu, Windows and macOS with Python 3.10-3.13, then the
`examples/simple_cache` walk-through through the installed CLI.

## Where things are

| Path | Contents |
|---|---|
| `the_judge/core/` | The verifier: evidence capture, sandbox, scoring, mutation, checklist |
| `the_judge/integrations/` | CLI, repair loop, agent runner, git hooks, VS Code, watch mode |
| `the_judge/hook.py` | Claude Code Stop hook |
| `plugin/` | Claude Code plugin: hook config, skill, slash commands |
| `tests/verdicts/` | What decides PASS / FAIL / ABSTAIN, false-PASS regressions |
| `tests/evidence/` | Independence, freeze, checklist, mutation, probes, contracts |
| `tests/sandbox/` | Test discovery, isolation, failure messages |
| `tests/integrations/` | Hook, improve, repair loop, critique, CLI output |
| `tests/packaging/` | Distribution contents, version, documentation checks |
| `tests/regression_audit/` | Labelled corpus: does a change make the judge less discriminating? |
| `eval_results/` | Pre-registered evaluations (archived evidence; do not edit) |

Architecture: [docs/architecture.md](docs/architecture.md).

## Rules for changes

- **A change to a verdict needs a test that shows it.** A wrong PASS is the worst bug this
  project can have. Every fix for one gets a regression test in `tests/verdicts/` that
  failed before the fix.
- **Do not weaken an existing test to make a change pass.** If a test is wrong, say why
  in the pull request.
- **Check the corpus when you touch `core/`:** `python tests/regression_audit/run_audit.py`
  should not get worse.
- **Docs must match the code.** `tests/packaging/test_docs.py` enforces part of this.
  README.md is also the PyPI page, so it uses absolute links only.
- **Update CHANGELOG.md** under the next version.

## Commits and pull requests

Commit messages: `type: summary` (`feat`, `fix`, `docs`, `test`, `refactor`, `build`,
`ci`), with a body that explains why. One topic per pull request; describe what changed
and how you tested it.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
