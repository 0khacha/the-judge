---
description: Review the project with The Judge and list what to improve, most important first
argument-hint: "[path]"
allowed-tools: Bash(judge improve:*), Bash(judge verify:*)
---

Run `judge improve ${ARGUMENTS:-.} --no-report` (a read-only review). Summarise the verdict,
the judge's next actions and the critique, most important first. Then ask the user
whether to work through them; if yes, follow the judge-loop skill until PASS.
