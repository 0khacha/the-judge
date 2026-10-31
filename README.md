<p align="center">
  <img src="https://raw.githubusercontent.com/0khacha/the-judge/main/logo.svg" width="180" alt="The Judge">
</p>

<h1 align="center">The Judge</h1>

<p align="center">
  <strong>Adversarial verification & continuous improvement engine</strong>
</p>
<p align="center">
  Drive any project to high quality through evidence-based evaluation and multi-round refinement
</p>
<p align="center">
  <a href="https://github.com/0khacha/the-judge/blob/main/LICENSE"><img src="https://img.shields.io/github/license/0khacha/the-judge?style=flat" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat" alt="Python 3.10+">
</p>

## Install

```bash
pip install the-judge-verify
```

> The PyPI project named `the-judge` is an **unrelated package** by another author.
> This project is published as **`the-judge-verify`**.

**Claude Code plugin** (after the pip install):

```text
/plugin install the-judge --marketplace 0khacha/the-judge
```

It adds a Stop hook that verifies every turn that changed code and sends the work back to
Claude with the judge's next actions until PASS, a skill with the test-first protocol, and
`/the-judge:verify`, `/the-judge:freeze`, `/the-judge:improve`. See the
[plugin guide](https://github.com/0khacha/the-judge/blob/main/PLUGIN_GUIDE.md).

**Other AI assistants.** Copy/paste into your AI assistant prompt:

```text
Run `pip install the-judge-verify` to install the verification tool, then read
AGENTS.md at https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
for the verification-repair loop protocol. After every critical code change,
run `judge verify . --json` and act on the findings.
```

Latest from `main` instead of the last release:

```bash
pip install git+https://github.com/0khacha/the-judge.git
```

mypy and ruff are **optional**. If they are on `PATH`, The Judge also runs them; if not,
those checks are skipped and reported as a `tooling` finding with reduced confidence,
and the decision is unaffected. To enable them: `pip install mypy ruff`.

Names: the distribution is `the-judge-verify`, the Python package is still
`import the_judge`, and the command is `judge`.

Check the [installation instructions](https://github.com/0khacha/the-judge/blob/main/INSTALL.md) for Claude Code, Cursor, Windsurf, Codex, Git hooks, VS Code, and CI/CD.

## What it does

**The Judge** is a verifier for AI coding agents. It runs your tests in an isolated
subprocess, refuses to count tests that were weakened, skipped or written to fit the
code, and answers every run with a verdict (PASS / FAIL / ABSTAIN) plus numbered,
machine-readable `next_actions` telling the agent exactly what to do next.

**Core loop**: `write tests → judge freeze → implement → judge verify → follow next_actions → repeat`

Since 1.0.2 it also looks for what the tests miss, and turns it into next actions:

- **Requirements checklist.** Every rule of `TASK.md` / `SPEC.md` / `REQUIREMENTS.md`
  (R1..Rn) needs a passing test that names it. `judge freeze` lists the rules no test
  covers yet, so they can be tested before the code exists.
- **Mutation feedback.** Before PASS, the judge plants small bugs in the code (`<` ->
  `<=`, `+` -> `-`, a removed `raise`, ...) and reruns the tests on a copy. Uncaught
  bugs come back as `add_test file.py:LINE` actions.

A bug is still only caught when some test exercises it; these two steps make the agent
write those tests.

**Measured so far** (pre-registered evaluations with Claude Haiku, raw data in
[`eval_results/`](https://github.com/0khacha/the-judge/tree/main/eval_results)):

- It has **not** been shown to make an agent's code more correct. On every benchmark
  tried -- small tasks, harder tasks with 41-149 hidden tests, and change requests in
  existing projects with hidden regression tests -- the agent without the judge already
  passed all hidden tests in 65 of 66 runs, leaving nothing to improve.
- As a gate it is accurate: 1.0.2 gave PASS to none of 36 wrong solutions, never a
  false FAIL, and no agent weakened a frozen test. The price is strictness: correct code
  gets ABSTAIN until each spec rule has a test, and a verify takes 10-20 s longer.
  Outside that benchmark, 1.0.2 could give a false FAIL on correct projects whose tests
  read fixtures via `__file__`, take over 30 s, or sit outside `testpaths`; these are
  fixed on `main` (see [CHANGELOG](https://github.com/0khacha/the-judge/blob/main/CHANGELOG.md)).

See [Known limitations](#known-limitations).

Works standalone or integrates with any AI coding assistant (Claude Code, Cursor, Windsurf, Aider, etc.) through the `AGENTS.md` protocol.

## What changes

### 1. Non-Visual Projects (Behavioral Verification)

<table>
<tr>
<td width="50%">

#### Without The Judge

> Implementation complete! All tests passed. The TTL expiration handles timestamps accurately, capacity eviction removes oldest entries, everything is ready for deployment.
>
> *(Hidden: TTL boundary check off by one. Expired keys stay valid.)*

</td>
<td width="50%">

#### With The Judge

```text
DECISION: FAIL
Score: 40.0 / 100.0

[1] [HIGH] Behavioral test failed:
    test_cache_expiration
    -> Review boundary logic in
       cache.py line 37.

Action: fix and re-verify.
```

</td>
</tr>
</table>

### 2. Visual Projects (Iterative Quality Engine)

| | Score | Notes |
|---|---|---|
| **Without The Judge** (baseline) | 52.0 / 100.0 | No nav, flat hierarchy, no stats, no tech tags |
| **With The Judge** (4 rounds) | 96.5 / 100.0 (+44.5 pts) | Sticky nav, stats bar, tech tags, contact card |

> **Note**: The visual-project numbers below come from an earlier version and were not
> re-tested for 1.0.1. Visual project scores are evaluated by screenshot analysis and require a browser
> (e.g., Playwright or Chrome). Without a browser available, visual projects produce `ABSTAIN`.
> The 52→96.5 improvement was captured in an environment with screenshot support.

<table>
<tr>
<td width="50%" align="center"><strong>Before</strong></td>
<td width="50%" align="center"><strong>After (4 rounds)</strong></td>
</tr>
<tr>
<td><img src="https://raw.githubusercontent.com/0khacha/the-judge/main/examples/alex_morgan_portfolio/before.png" alt="Before The Judge" width="100%"></td>
<td><img src="https://raw.githubusercontent.com/0khacha/the-judge/main/examples/alex_morgan_portfolio/after.png" alt="After The Judge" width="100%"></td>
</tr>
</table>

*These numbers came from a built-in heuristic improver that 1.1.0 removed (it could only
make cosmetic edits). To reproduce a multi-round run, let an agent make the changes:
`judge improve examples/alex_morgan_portfolio/ --agent` (requires a browser for screenshots).
`judge improve` without `--agent` is a read-only review and changes no files.*

## The rules

10 rules enforced by The Judge:

1. **Never trust self-claims.** PASS needs tests that were fixed before the implementation (`judge freeze` or a git commit). Discrepancy detection between agent claims and ground-truth evidence requires the caller to provide external `agent_claims` via the `verify()` API.
2. **Execute in anonymous sandboxes.** Strip process markers and inspection flags.
3. **Synthesize challenge probes.** A few keyword-triggered probes add checks on top of your tests.
4. **Enforce requirement contracts.** Unverified critical requirements trigger ABSTAIN.
5. **Detect tampering.** Block conftest hijacking, sys.modules manipulation, TOCTOU symlinks.
6. **Track regressions.** Flag fixed bugs broken again in subsequent rounds.
7. **Return next actions.** Every verdict has numbered `next_actions` (fix_code with the failing assertion, restore_tests, freeze_tests, stop, ...).
8. **Predictable exit codes.** 0 = PASS, 1 = FAIL, 2 = ABSTAIN, 3 = ERROR.
9. **No false guarantees.** Verification proves evidence under tested conditions, not mathematical proof.
10. **Vendor-neutral.** Works with any agent via JSON CLI or Python API.

## Usage

```bash
judge verify .                 # Human-readable report
judge verify . --json          # Machine-readable JSON for agents
judge contract .              # Inspect requirement coverage
judge improve .               # Read-only review: verdict, next actions, critique
judge improve . --agent       # A coding agent fixes, the judge re-verifies, until PASS
judge demo                    # 60-second interactive demo
```

### Plugin commands

```bash
judge hook install            # Pre-commit verification hook
judge hook install --pre-push # Pre-push verification hook
judge hook run                # Claude Code Stop hook (reads the event JSON from stdin)
judge init vscode             # Generate VS Code tasks
judge watch .                 # Re-verify on every file save
```

### Requirement contract (judge.json)

```json
{
  "name": "cache-service",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Evict expired keys after TTL seconds elapse.",
      "category": "boundary",
      "priority": "critical",
      "properties": ["cache_expiration"]
    }
  ]
}
```

### Python API

```python
from the_judge import verify

result = verify(".", task_spec=None)
print(result.decision, result.numeric_score, result.findings)

# To enable discrepancy detection against agent claims:
result = verify(".", task_spec=None, agent_claims={
    "requirements": [{"id": "REQ-001", "status": "pass", "evidence": "test_cache"}],
    "edge_cases": [], "security_notes": [],
})
```

### Iterative improvement API

```python
from the_judge import improve

# A coding agent makes the changes; the judge verifies after every round.
result = improve(".", agent_command="claude -p --permission-mode acceptEdits", max_rounds=4)
print(result["outcome"], result["final_decision"])
```

With your own repair step and quality bar:

```python
from the_judge.integrations import AgentRepairLoop

def review_quality(workspace, verification):
    # Supply evidence from a UX, accessibility, visual, or maintainability review.
    return {
        "score": 82,
        "passed": False,
        "weaknesses": ["Keyboard focus is not visible on the primary action."],
    }

def improve_from_feedback(workspace, feedback):
    # Your agent's repair logic: read feedback["findings"] and feedback["critique"],
    # edit the workspace files, then return True when a change was made.
    return False  # stub — replace with real improvement logic

loop = AgentRepairLoop(quality_threshold=90, quality_evaluator=review_quality)
result = loop.run_repair_loop(".", agent_repair_func=improve_from_feedback)
```

The loop gives the repair callback both Judge findings and quality weaknesses, verifies each changed round once, preserves regression evidence, and stops at the threshold or when a callback cannot make a meaningful workspace change.

## How it works

```text
write tests from the spec -> judge freeze . -> implement -> judge verify . --json
                                                               |
   PASS    -> next_actions: done                               |
   FAIL    -> next_actions: fix_code <test> "<assertion>" -----+  (fix the code, not the test)
   ABSTAIN -> next_actions: cover_requirement R4 "<rule>" -----+  (spec rule without a test)
              next_actions: add_test grade.py:12 "'>=' -> '>'"-+  (planted bug no test caught)
              next_actions: what other evidence is missing ----+
   stuck   -> next_actions: stop (3 identical results, or 5 runs without PASS)
```

The agent follows [AGENTS.md](https://github.com/0khacha/the-judge/blob/main/AGENTS.md): it
writes tests first, freezes them, implements, verifies, and does what `next_actions[0]`
says. Each run is compared with the previous one (`.judge/history.json`): tests that
passed before and fail now are reported as regressions. The optional `AgentRepairLoop` can also accept a quality evaluator for UX, visual quality, accessibility, or maintainability, so a passing implementation continues through meaningful improvement rounds until it reaches the configured quality bar. Maximum 5 rounds by default.

## Documentation

### Getting Started
- [Quick Start Guide](https://github.com/0khacha/the-judge/blob/main/docs/QUICK_START.md) - Get started in 5 minutes
- [Installation Guide](https://github.com/0khacha/the-judge/blob/main/INSTALL.md) - Platform-specific setup
- [Plugin Integration Guide](https://github.com/0khacha/the-judge/blob/main/PLUGIN_GUIDE.md) - Integrate into any IDE or CLI

### Reference
- [Python API Reference](https://github.com/0khacha/the-judge/blob/main/docs/API.md) - Complete API documentation
- [Agent Integration Protocol](https://github.com/0khacha/the-judge/blob/main/AGENTS.md) - AI assistant integration
- [CLI Commands](https://github.com/0khacha/the-judge/blob/main/AGENTS.md#quick-reference) - Command reference
- [Integration Examples](https://github.com/0khacha/the-judge/blob/main/examples/INTEGRATION_EXAMPLES.md) - Real-world usage

### Advanced
- [Architecture Specification](https://github.com/0khacha/the-judge/blob/main/docs/architecture.md) - System design
- [Development Guide](https://github.com/0khacha/the-judge/blob/main/CONTRIBUTING.md) - Contributing guide
- [Security Model](https://github.com/0khacha/the-judge/blob/main/SECURITY.md) - Security boundaries
- [Threat Model](https://github.com/0khacha/the-judge/blob/main/THREAT_MODEL.md) - Attack surface
- [Full Documentation Index](https://github.com/0khacha/the-judge/tree/main/docs) - All documentation

## Judge probes

The Judge runs your workspace's own tests (discovered recursively, honouring your
pytest configuration) and, where it recognises a familiar shape, adds a small number
of **judge probes**. Probe triggers are **heuristic and keyword-based**: they fire on
parameter and method *names*. The same logic under other names gets no probe. Every
report lists the probes that ran (with their outcome) and, per public class or
function, the probe kinds that did **not** run because no trigger matched
(`trust_profile.probe_coverage` in `--json`, the "JUDGE PROBES" section in the
human report).

| Probe | Trigger (keyword-based) | What it asserts |
|---|---|---|
| **Rollback** | Class with `begin`/`start`/`checkpoint`/`savepoint`, `rollback`/`revert`/`abort`/`undo`, `set`/`put`/`write` and `get`/`read` methods | A write made after the checkpoint is undone; earlier state survives. Single level only. |
| **Expiration** | Class whose `__init__` has `ttl`/`ttl_seconds`/`expire`/`expiry`, with a writer and a reader method, in a module whose clock is `time.time`/`time.monotonic` | With ttl=1, after the clock is advanced by 10⁷ s the stored value is no longer returned. |
| **Capacity** | Class whose `__init__` has `capacity`/`max_size`/`limit`/`bound`, an insert method (`push`/`add`/`enqueue`/`put`/…) and `__len__` or a reader | With capacity 2, at most 2 of 3 inserted items are retained. |
| **Idempotency** | Function with one `str`-annotated parameter whose name contains `sanitize`/`clean`/`strip`/`normalize`/`purify`/`harden` | `f(f(x)) == f(x)` on a few sample strings. |

Rules every probe follows:

- A probe invents its inputs, so an exception on those inputs means *not applicable*
  (the probe is skipped and is not evidence), never *defect found*. Constructors are
  built from the signature; a probe is skipped when a required argument can't be
  satisfied.
- Every probe has an unconditional assertion that fails on the defect it names. A
  meta-test (`tests/test_audit_p1_5_probe_soundness.py`) checks that each probe kind
  passes a correct implementation and fails a defective one.

Probes that existed before and were **removed** because they failed correct code or
could not fail at all: boundary perturbation, uniqueness, generic idempotency on any
function, multi-input variance, and state isolation.

### What this means for verdicts

- **PASS needs independent evidence**: at least one passing, non-vacuous workspace test
  that was fixed *before* the implementation, i.e. unchanged since `judge freeze` (or the
  last git commit) while an implementation file changed afterwards. Tests written after
  the code must pass, but cannot earn PASS on their own. Judge probes add checks but are
  not required.
- **FAIL** means a test failed, a frozen/committed test was weakened or deleted, a test
  result was rewritten by a hook, or a test that passed in the previous run fails now.
- **ABSTAIN** means the evidence is insufficient, and `next_actions` lists, as numbered
  steps, what would turn it into a verdict (write tests, freeze them, unskip, ...).
- **Tests that prove nothing are not evidence.** Skipped/xfail tests, tests without a real
  assertion, tautologies and `is not None`-only tests are reported and not counted.
- **Static analysis is advisory.** mypy/ruff findings are `static_analysis` warnings;
  they never decide the verdict. If the tools are not installed, nothing changes.
- **`judge.json` requirements** are VERIFIED only by a passing test that names them.

## Known limitations

- **Bugs are only caught by tests.** The Judge does not invent oracles: a wrong comparison,
  rounding mode, race condition or missing edge case is found only if a test exercises
  it. The checklist and mutation feedback push the agent to write those tests; they do
  not write them. The four judge probes (rollback, expiration, capacity, idempotency) are
  keyword-triggered and rarely apply.
- **Checklist: mention, not meaning.** A test covers rule R4 when its source names `R4`;
  the judge cannot check that the test really exercises the rule. Rules are taken from
  list items only; prose requirements outside lists are not numbered.
- **Mutation: sample and threshold.** At most 25 mutants per run, spread over lines.
  Some mutants are equivalent (cannot be caught), hence the 85% threshold. Mutation finds
  code no test checks, not behaviour the code lacks. It adds one pytest run per mutant
  (about 10-20 s on a small project); `--no-mutation` skips it.
- **Independence is a protocol, not a proof.** An agent can write the code first, then
  tests fitted to it, freeze them, and make a token change to the code; the rule
  "unchanged since freeze, code changed afterwards" is then satisfied. Every freeze is
  recorded in `.judge/frozen.json`, but intent cannot be verified.
- **Hard-coded outputs: narrow detection.** PASS is withheld when every literal assertion
  of the independent tests (`assert f(1, 2) == 3`) is answered by a dict literal or
  if-return chain in the code. Lookup tables built at run time, string-encoded tables,
  or assertions built from parametrize arguments are not detected.
- **Result rewriting: runtime detection only.** A conftest/plugin that turns a raised
  test into "passed" is caught by the sandbox's own hooks. A hostile plugin that
  disables those hooks, or that alters what pytest collects in ways other than
  removing whole test functions (for example dropping individual parametrize cases),
  is not detected.
- **Tampering outside git and freeze is invisible.** Without a freeze snapshot or a git
  baseline, a weakened-but-still-meaningful assertion cannot be noticed.
- **What the sandbox copies.** Tests run from a temporary copy of the test files, their
  conftest/helper modules, everything else under the test directories, and the
  project's other non-Python files, at most 5 MB per file and 50 MB in total (files
  near the tests first). It is not a git checkout and holds no implementation `.py`
  copies, so tests that run `git` or read source files via `__file__` see a
  difference. The run may take 300 s (`--timeout`); a run stopped at the limit is
  ABSTAIN.
- **The sandbox is not a security boundary.** Tests run in a separate process with a
  temporary collection directory and a reduced environment, but hostile code can still
  detect it, read files or use the network.
- **State in the workspace.** `judge freeze` and `judge verify` write `.judge/` (frozen
  tests, history). Add it to `.gitignore` or commit it deliberately.

## Project Status

**Status**: v1.1.0 · MIT License · Python 3.10+

## Contributing

Contributions welcome! See [CONTRIBUTING.md](https://github.com/0khacha/the-judge/blob/main/CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/0khacha/the-judge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0khacha/the-judge/discussions)
- **Changelog**: [CHANGELOG.md](https://github.com/0khacha/the-judge/blob/main/CHANGELOG.md)

## License

[MIT License](https://github.com/0khacha/the-judge/blob/main/LICENSE) -- Copyright (c) 2026 **@0khacha**
