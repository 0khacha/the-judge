# the-judge-verify 1.0.2 build (not published)

Built from commit `1a3bfa1` with `python -m build`; `twine check --strict` PASSED for both.

| File | SHA-256 |
|---|---|
| the_judge_verify-1.0.2-py3-none-any.whl | 3f8e624c64fe69983a5acef80b54af2ae85e68c70034d10332037084a1f1d56e |
| the_judge_verify-1.0.2.tar.gz | 3947479fe2ea269ed02f9d70b2e9c8765131e7cdbfc455ca8422373155896497 |

Clean-venv check: wheel installed with pytest into a fresh venv; `judge --version` prints
`The Judge v1.0.2`; freeze prints the requirements checklist; verify returns
`cover_requirement` for an uncovered rule.

Changes since 1.0.1: vacuous-test false positives fixed; a re-freeze no longer erases
earlier independence; requirements checklist; mutation feedback; `--no-mutation`,
`--no-requirements`.
