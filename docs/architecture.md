# Architecture

The Judge separates **untrusted** work (the agent's code and tests, run in a subprocess)
from **trusted** judgement (evidence, scoring, next actions, in the judge's own
process). An agent never sees how the verdict is computed, only what to do next.

```text
 agent / user ──► judge verify . ─────────────────────────────────────────────┐
                    │                                                         │
                    ▼                                                         │
   capture_evidence (core/evidence.py)                                        │
     ├─ test_discovery   which files pytest would collect                     │
     ├─ property_engine  keyword-triggered judge probes (rollback, ttl, ...)  │
     ├─ sandbox          tests + probes in a subprocess, collected from a     │
     │                   temp dir, with hooks that catch rewritten results    │
     ├─ baseline         tests weakened since the git baseline?               │
     ├─ independence     tests unchanged since `judge freeze`, code changed   │
     ├─ hardcoding       implementation that just returns the expected values │
     └─ mypy / ruff      advisory only                                        │
                    │                                                         │
                    ▼                                                         │
   score_engine      hard gates (failures, tampering, regressions) + score    │
   contract_engine   judge.json requirements: VERIFIED only by a named test   │
   checklist         TASK/SPEC/REQUIREMENTS.md rules R1..Rn need a test       │
   mutation          before PASS: plant bugs, rerun, ≥85% must be caught      │
   history           .judge/history.json: regressions, stuck detection        │
                    │                                                         │
                    ▼                                                         │
   VerificationResult: PASS | FAIL | ABSTAIN, score, findings, next_actions ◄─┘
```

## Who calls the verifier

| Caller | Module | What happens with the verdict |
|---|---|---|
| `judge verify` | `integrations/cli.py` | Report or JSON; exit code 0 PASS, 1 FAIL, 2 ABSTAIN, 3 error. |
| Claude Code Stop hook | `hook.py` | Not PASS: the turn is sent back to Claude with the next actions. |
| `judge improve --agent` | `integrations/repair_loop.py`, `agent_runner.py` | Next actions become the agent's prompt; re-verify after each round. |
| `judge improve` | same, one round | Read-only review with next actions and critique. |
| git hooks, `judge watch`, VS Code tasks | `hooks.py`, `watcher.py`, `ide.py` | Block the commit / print the verdict. |

The critique (`core/critique_engine.py`) is a second opinion used by `improve`. It
classifies weaknesses by evidence level and never changes the verdict.

## Package layout

```text
the_judge/
├── api.py                 verify(), freeze(), improve(), critique()
├── hook.py                Claude Code Stop hook
├── core/
│   ├── evidence.py        evidence capture (orchestrates the modules below)
│   ├── sandbox.py         subprocess isolation and result-rewrite detection
│   ├── test_discovery.py  pytest-compatible test discovery
│   ├── property_engine.py keyword-triggered judge probes
│   ├── baseline.py        tampering relative to git
│   ├── independence.py    judge freeze and independent evidence
│   ├── hardcoding.py      hard-coded expected outputs
│   ├── checklist.py       spec rules R1..Rn
│   ├── contract_engine.py judge.json requirement coverage
│   ├── mutation.py        mutation feedback
│   ├── score_engine.py    hard gates, score, verdict
│   ├── next_actions.py    numbered next actions
│   ├── history.py         iteration history, regressions, stuck
│   ├── critique_engine.py independent critique (improve)
│   ├── visual_engine.py   screenshots for visual projects
│   └── decision.py        VerificationResult, Finding
├── integrations/
│   ├── cli.py             the `judge` command
│   ├── repair_loop.py     multi-round loop (AgentRepairLoop)
│   ├── agent_runner.py    runs a coding agent for --agent
│   ├── agent_adapter.py   result -> agent feedback
│   ├── audit_trail.py, progress_report.py   per-round record and HTML report
│   ├── hooks.py, ide.py, watcher.py, demo.py
└── schemas/               JSON schemas for task, evidence and result
```

Outside the package: `plugin/` (Claude Code plugin: hook config, skill, commands),
`.claude-plugin/marketplace.json`, `examples/`, `eval_results/` (pre-registered
evaluations), `tests/` (including `tests/regression_audit`, a labelled corpus).

## Invariants

- **Static analysis never decides.** mypy and ruff findings are advisory.
- **PASS needs independent evidence**: a passing, non-vacuous test unchanged since
  `judge freeze` or the last commit, with the implementation changed afterwards.
- **Weakened evidence is FAIL**: a frozen or committed test deleted, skipped or
  weakened, or a test result rewritten by a hook.
- **The sandbox is isolation, not security.** See [SECURITY.md](../SECURITY.md) and
  [threat-model.md](threat-model.md).
