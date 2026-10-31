# the-judge-verify 1.1.0

Published to PyPI on 2026-10-31: https://pypi.org/project/the-judge-verify/1.1.0/
(the first release since 1.0.0; 1.0.1 and 1.0.2 were built but never uploaded).

Built from merge commit `2a55850` (tag `v1.1.0`), in a clean clone of `main`, with
`python -m build`. `twine check --strict` PASSED for both files. The hashes PyPI reports
are identical to the local build.

| File | SHA-256 |
|---|---|
| the_judge_verify-1.1.0-py3-none-any.whl | 596999b352d8d393c1ae16d36392ed6e8c9c3f46fe8eb214b9f52b641f10157e |
| the_judge_verify-1.1.0.tar.gz | 55c0a78dec84a6ad9b64c15b9059115051fe2b4f8e30f332c62c2ab6a702596e |

Checks:

- **Clean venv from the local wheel**
  - `judge --version` prints `The Judge v1.1.0`.
  - Walk-through `examples/simple_cache`: freeze; the off-by-one solution gets FAIL
    (exit 1); the Stop hook returns `"decision": "block"`; the correct solution gets PASS
    (exit 0).
  - `judge improve --apply` prints the removal notice.
- **Clean venv from PyPI**: `pip install the-judge-verify==1.1.0`, then `judge --version`
  prints `The Judge v1.1.0`.
- **CI on the release commit**: 14/14 checks passed (tests on Ubuntu, Windows and macOS
  with Python 3.10-3.13, plus the walk-through job).

Changes: see the CHANGELOG. In short: the Claude Code plugin with its Stop hook,
`judge improve --agent`, removal of `AutoImprover` / `--apply`, dead code and stale
material removed, a fix for truncated failure messages under pytest 9.2, and Python
3.10+ required.
