# the-judge-verify 1.0.1 build record (not published)

Built from commit 93baa60 (`build: bump version to 1.0.1`) with a clean working tree.

| File | SHA-256 |
|---|---|
| `the_judge_verify-1.0.1-py3-none-any.whl` | `50fa8c4b54e3c02e388038b20b37658f81f48b3af6a4d7ad494de6d3a2073d68` |
| `the_judge_verify-1.0.1.tar.gz` | `8f05965427462776f8b42de463a2010ee52084ecd724ad50e4c471fae33a6118` |

Checks:
- `twine check --strict dist/*` with `readme_renderer[md]` installed: both PASSED; README renders with 5 images and no relative links.
- Clean venv, `pip install <wheel>`: pulls pytest; `judge --version` = 1.0.1; `judge freeze` -> buggy code FAIL with next_actions[0] = fix_code test_rem (assertion quoted) -> fixed code PASS, loop.iteration 2, newly_passing [test_rem].
- Full test suite on 93baa60: all passed with mypy/ruff on PATH and all passed (1 mypy-only test skipped) without them.

This exact wheel is the one installed in the evaluation-2 venv. Any later README-only
rebuild changes these hashes; the code is unchanged (see REPORT2.md).
