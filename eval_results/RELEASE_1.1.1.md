# the-judge-verify 1.1.1

Published to PyPI on 2026-10-31: https://pypi.org/project/the-judge-verify/1.1.1/

A documentation release. It puts the rewritten README on the PyPI project page; the 1.1.0
page linked files that moved in the docs reorganization. Since `v1.1.0`, the package code
changed only in its version number (`the_judge/_version.py`, `pyproject.toml`).

Built from merge commit `91a0e17` (tag `v1.1.1`), in a clean clone of `main`, with
`python -m build`. `twine check --strict` PASSED for both files. The hashes PyPI reports
are identical to the local build.

| File | SHA-256 |
|---|---|
| the_judge_verify-1.1.1-py3-none-any.whl | e709767251c707b0aaaca29233969043145df0b314632c2edae6c397797c28e4 |
| the_judge_verify-1.1.1.tar.gz | 46f0e07d7db9e69a54f0461dda1f96914f72e3eea609105f2978c8aeca9d0877 |

Checks:

- **Clean venv from the local wheel**
  - `judge --version` prints `The Judge v1.1.1`.
  - Walk-through `examples/simple_cache`: freeze; the off-by-one solution gets FAIL
    (exit 1); the Stop hook returns `"decision": "block"`; the correct solution gets PASS
    (exit 0).
  - The package metadata (README) links the new `docs/` paths.
- **Clean venv from PyPI**: `pip install the-judge-verify==1.1.1`, then `judge --version`
  prints `The Judge v1.1.1`. The project page shows the new README.
- **CI on `main`** before the version bump: 13/13 checks passed.
