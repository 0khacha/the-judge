---
description: Freeze the current tests with The Judge before implementing
argument-hint: "[path]"
allowed-tools: Bash(judge freeze:*), Bash(pip install the-judge-verify)
---

Run `judge freeze ${ARGUMENTS:-.}`. Show which tests were frozen and which spec rules
(R1..Rn) no test names yet. If rules are missing, offer to write tests for them (expected
values from the spec, the rule id in a comment) and freeze again before any
implementation change.
