---
description: Verify the project with The Judge and act on its next actions
argument-hint: "[path]"
allowed-tools: Bash(judge verify:*), Bash(judge freeze:*), Bash(pip install the-judge-verify)
---

Run `judge verify ${ARGUMENTS:-.} --json` (install with `pip install the-judge-verify` if
`judge` is missing). Report the decision and `numeric_score`, then follow
`next_actions` in order as described in the judge-loop skill, re-verifying after each
change, until the decision is PASS or the first action is `stop`. Never weaken a frozen
test.
