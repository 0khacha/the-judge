<p align="center">
  <img src="https://raw.githubusercontent.com/0khacha/the-judge/main/logo.svg" width="160" alt="The Judge">
</p>

<h1 align="center">The Judge</h1>

<p align="center">
  <strong>An independent verifier for code written by AI agents.</strong><br>
  It runs your tests in a sandbox, rejects evidence that was weakened or written to fit
  the code, plants bugs to find what the tests miss, and tells the agent exactly what
  to do next.
</p>

<p align="center">
  <a href="https://pypi.org/project/the-judge-verify/"><img src="https://img.shields.io/pypi/v/the-judge-verify?style=flat" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=flat" alt="Python 3.10+">
  <a href="https://github.com/0khacha/the-judge/actions/workflows/ci.yml"><img src="https://github.com/0khacha/the-judge/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/0khacha/the-judge/blob/main/LICENSE"><img src="https://img.shields.io/github/license/0khacha/the-judge?style=flat" alt="MIT License"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#claude-code-plugin">Claude Code plugin</a> ·
  <a href="#what-the-judge-checks">What it checks</a> ·
  <a href="#known-limitations">Limitations</a> ·
  <a href="https://github.com/0khacha/the-judge/blob/main/docs/README.md">Docs</a>
</p>

---

## Why

A coding agent says *"done, all tests pass"*. That sentence can be true and still mean
nothing:

- the tests were written **after** the code, to match what it does;
- a failing test was **deleted, skipped or weakened**;
- a test **asserts nothing**, or only that a value is not `None`;
- a rule of the spec **has no test at all**;
- an off-by-one at a boundary is **checked by no test**.

The Judge looks for each of these. It answers **PASS** only on independent evidence:
tests fixed *before* the implementation, still intact, actually asserting something, and
strong enough to catch bugs planted in the code. Anything less is **FAIL** or
**ABSTAIN**, with numbered `next_actions` the agent can act on.

## Quick start

```bash
pip install the-judge-verify
```

> The PyPI project `the-judge` is an **unrelated package**. This one is
> **`the-judge-verify`**: the import is `import the_judge` and the command is `judge`.

### With Claude Code

```text
/plugin install the-judge --marketplace 0khacha/the-judge
```

Then ask for work the usual way, test-first: *"Implement `parse_duration` from SPEC.md.
Write the tests first and freeze them with the judge."* Claude writes the tests and runs
`judge freeze .`, then implements. When it tries to finish, the
[Stop hook](#claude-code-plugin) verifies the change and sends the turn back with the
judge's next actions until the verdict is PASS.

### Any project, from the terminal

```bash
judge freeze .           # 1. freeze the tests (write them from the spec first)
                         # 2. implement or change the code
judge verify .           # 3. PASS / FAIL / ABSTAIN + what to do next
```

### Other agents (Cursor, Windsurf, Codex, Aider, ...)

Copy/paste into your AI assistant prompt:

```text
Run `pip install the-judge-verify` to install the verification tool, then read
AGENTS.md at https://raw.githubusercontent.com/0khacha/the-judge/main/AGENTS.md
for the verification-repair loop protocol. After every critical code change,
run `judge verify . --json` and act on the findings.
```

Setup for each tool: [installation guide](https://github.com/0khacha/the-judge/blob/main/docs/installation.md).
Latest from `main`: `pip install git+https://github.com/0khacha/the-judge.git`.

## See it work

From [`examples/simple_cache`](https://github.com/0khacha/the-judge/blob/main/examples/simple_cache/README.md):
a TTL cache whose spec says an entry is valid *until exactly* `ttl_seconds` have passed.

```text
$ judge freeze .
Froze 7 test(s) into .judge/frozen.json
Requirements checklist (5 rules from the spec; ...):
  [covered] R4 (SPEC.md): An entry is returned until exactly `ttl_seconds` have passed ...

$ judge verify .            # implementation that expires at exactly ttl (off by one)
DECISION: FAIL
Numeric Trust Score: 40.0 / 100.0
NEXT ACTIONS
  1. [fix_code] AssertionError: assert None == 'v'  (test: test_entry_valid_until_exactly_ttl)

$ judge verify .            # after the fix
DECISION: PASS
Numeric Trust Score: 94.0 / 100.0
NEXT ACTIONS
  1. [done] PASS: all tests passed, including 7 independent test(s) fixed before the
     implementation. The tests caught 5 of 5 planted bugs.
```

## Verdicts

| Verdict | Exit | Meaning |
|---|:-:|---|
| **PASS** | 0 | Tests fixed before the implementation pass, nothing was tampered with, every spec rule has a test, and the tests caught at least 85% of the planted bugs. Strong evidence, not a proof. |
| **FAIL** | 1 | A test fails, a test passed before and fails now, or a test was deleted, skipped, weakened or had its result rewritten. |
| **ABSTAIN** | 2 | Not enough independent evidence. `next_actions` says exactly what is missing. |
| ERROR | 3 | The judge could not run (for example, a wrong path). |

Every verdict carries numbered `next_actions`, for example:

| Action | What the agent should do |
|---|---|
| `fix_code` / `fix_regression` | Change the **implementation** so the named test passes |
| `restore_tests` | Undo its change to a frozen test |
| `freeze_tests` | Write tests from the spec and freeze them **before** implementing |
| `cover_requirement` | Spec rule `R4` has no test that names it: write one |
| `add_test` | A planted bug at `cache.py:45` (`>` -> `>=`) went unnoticed: add a test from the spec |
| `stop` | The loop is stuck (3 identical results, or 5 runs without PASS): report to the user |

The full protocol agents follow is in [AGENTS.md](https://github.com/0khacha/the-judge/blob/main/AGENTS.md).

## What the judge checks

| Check | What it catches |
|---|---|
| **Independent evidence** | Tests written to fit the code. A test counts only if it is unchanged since `judge freeze` (or the git baseline) and the implementation changed afterwards. |
| **Tampering** | Tests deleted, skipped, weakened, or parametrized away since the freeze or the git baseline; a conftest or plugin that rewrites a failed result into a pass. |
| **Vacuous tests** | Tests with no real assertion, tautologies, `is not None`-only checks, and tests that never touch the project's code. These are reported and not counted. |
| **Requirements checklist** | List items in `TASK.md`, `SPEC.md` or `REQUIREMENTS.md` become rules R1..Rn. Each needs a passing test that names its id (`def test_expiry():  # R4`). |
| **Mutation testing** | Before PASS, the judge plants small bugs (`<` -> `<=`, `+` -> `-`, a removed `raise`, ...) in a copy of the project. If fewer than 85% are caught, each surviving bug becomes an `add_test` action. |
| **Hard-coded outputs** | Implementations that answer every literal assertion from a lookup table or an `if`-chain instead of computing it. |
| **Regressions and loops** | Each run is compared with the previous one (`.judge/history.json`): tests that passed before and fail now, and loops that are stuck. |
| **`judge.json` contracts** | Requirements with a priority. A critical requirement without a passing test that names it means ABSTAIN. |
| **Judge probes** | A few extra checks the judge generates itself (rollback, expiry, capacity, idempotency). They are triggered by method and parameter names. |
| **Static analysis** | mypy and ruff are **optional** and advisory: if installed they run, but they never decide the verdict. |

The tests run in a separate subprocess, collected from a temporary directory, with a 300 s
limit (`--timeout`). How a verdict is computed: [architecture](https://github.com/0khacha/the-judge/blob/main/docs/architecture.md).

## Claude Code plugin

```text
/plugin install the-judge --marketplace 0khacha/the-judge
```

| Component | What it does |
|---|---|
| **Stop hook** | When Claude finishes a turn that changed code, it runs `judge verify`. Unless the verdict is PASS, Claude Code hands the judge's next actions back to Claude, which keeps working. |
| **`judge-loop` skill** | Teaches Claude the protocol: tests from the spec first, freeze, implement, verify, follow `next_actions`, never weaken a frozen test. |
| **`/the-judge:freeze`** | Freeze the tests and list spec rules no test covers yet. |
| **`/the-judge:verify`** | Verify, then work through `next_actions` until PASS. |
| **`/the-judge:improve`** | Read-only review: verdict, next actions and critique, most important first. |

How the hook decides:

- **Opt-in per project.** It acts only where a `.judge/` folder exists (`judge freeze`
  creates it). `THE_JUDGE_HOOK=always` turns it on everywhere, `THE_JUDGE_HOOK=off` turns
  it off.
- **Only after changes.** A turn that changed no source, test or spec file is not verified
  again.
- **Bounded.** When the judge reports the loop as stuck, Claude is allowed to stop and the
  user is told why. Errors inside the hook never break the session.

Details and troubleshooting: [plugin guide](https://github.com/0khacha/the-judge/blob/main/docs/claude-code-plugin.md).

## Let an agent do the fixing

```bash
judge improve .                     # read-only review: verdict, next actions, critique
judge improve . --agent             # Claude Code makes the changes, the judge re-verifies
judge improve . --agent "aider --yes-always --message-file {prompt_file}"
```

Each round, the agent gets the verdict's next actions as its prompt, on stdin or in
`{prompt_file}`. The judge verifies independently after the agent finishes. The loop ends
on PASS, after `--max-rounds` (default 5), or when the agent fails or changes nothing.
For web pages, each round also saves a screenshot (with the optional `visual` extra and
Playwright).

## CLI

| Command | |
|---|---|
| `judge freeze .` | Freeze the current tests; show spec rules without a test |
| `judge verify . [--json]` | Verify; `--baseline REF`, `--timeout N`, `--no-mutation`, `--no-requirements` |
| `judge improve . [--agent [CMD]]` | Review, or an agent-driven repair loop |
| `judge contract .` | Requirement coverage of `judge.json` |
| `judge critique .` | Independent critique: weaknesses by evidence level |
| `judge hook install [--pre-push]` | Git hook that blocks commits (or pushes) that do not PASS |
| `judge hook run` | The Claude Code Stop hook (reads the event JSON on stdin) |
| `judge watch .` | Re-verify on every save |
| `judge init vscode` | VS Code tasks |
| `judge demo` | A 60-second demo |

## Python API

```python
import the_judge

result = the_judge.verify(".")
print(result.decision, result.numeric_score)      # e.g. ABSTAIN 65.0
for action in result.next_actions:
    print(action["step"], action["action"], action["detail"])

# Let a coding agent act on the findings until PASS:
the_judge.improve(".", agent_command="claude -p --permission-mode acceptEdits", max_rounds=4)
```

`freeze()`, `critique()`, repair callbacks and quality evaluators:
[Python API](https://github.com/0khacha/the-judge/blob/main/docs/python-api.md) ·
[recipes](https://github.com/0khacha/the-judge/blob/main/docs/recipes.md).

## Results so far

The Judge is tested in pre-registered evaluations with Claude Haiku as the coding agent
(protocols hashed before any task existed; raw data in
[eval_results](https://github.com/0khacha/the-judge/blob/main/eval_results/README.md)).

- **As a gate it is accurate.** 1.0.2 gave PASS to none of the wrong solutions in 45
  checks, never gave a false FAIL there, and no agent weakened a frozen test. (1.0.1, before
  the checklist and mutation testing, passed 10 of 12 wrong solutions.)
- **It has not been shown to make an agent's code more correct.** On every benchmark tried,
  the agent without the judge already passed the hidden tests in 65 of 66 runs, leaving
  nothing to improve.
- **The price is strictness.** Correct code gets ABSTAIN until each spec rule has a test,
  and mutation testing adds about 10-20 s per verify on a small project.

## Known limitations

- **Bugs are caught only by tests.** The judge does not invent oracles. A wrong rounding
  mode or a race condition is found only if some test exercises it; the checklist and
  mutation testing push the agent to write those tests.
- **Mentioning a rule is not testing it.** A test covers R4 when its source names `R4`; the
  judge cannot check that the test exercises that rule.
- **Independence is a protocol, not a proof.** An agent can write code, then fitted tests,
  freeze them and make a token change. Every freeze is recorded, but intent cannot be
  verified.
- **PASS needs Python.** A test counts as evidence only when it exercises a Python module
  of the project. A pure HTML/CSS/JS project can get FAIL and a screenshot review, but not
  PASS.
- **Mutation testing samples.** At most 25 planted bugs per run; some cannot be caught by
  any test (equivalent mutants), hence the 85% threshold.
- **Hard-coding detection is narrow.** It looks at dict literals and `if`-chains that answer
  literal assertions; tables built at run time, or assertions built from parametrize
  arguments, are not analysed.
- **Probes are keyword-triggered.** The four judge probes run only when method and
  parameter names match, so they rarely apply.
- **The sandbox isolates; it is not a security boundary.** Hostile code can still detect
  it, read files or use the network. See [SECURITY.md](https://github.com/0khacha/the-judge/blob/main/SECURITY.md).
- **State in your project.** `judge freeze` and `verify` write `.judge/` (frozen tests,
  history). Commit it deliberately or add it to `.gitignore`.

## Documentation

| | |
|---|---|
| [Quick start](https://github.com/0khacha/the-judge/blob/main/docs/quick-start.md) | First verification in five minutes |
| [Installation](https://github.com/0khacha/the-judge/blob/main/docs/installation.md) | Claude Code, Cursor, Windsurf, Codex, git hooks, VS Code, CI |
| [Claude Code plugin](https://github.com/0khacha/the-judge/blob/main/docs/claude-code-plugin.md) | Hook behaviour, commands, `judge improve --agent` |
| [Python API](https://github.com/0khacha/the-judge/blob/main/docs/python-api.md) · [Recipes](https://github.com/0khacha/the-judge/blob/main/docs/recipes.md) | Programmatic use and copy-paste integrations |
| [Architecture](https://github.com/0khacha/the-judge/blob/main/docs/architecture.md) · [Threat model](https://github.com/0khacha/the-judge/blob/main/docs/threat-model.md) | How verdicts are computed; what is defended against |
| [Examples](https://github.com/0khacha/the-judge/blob/main/examples/README.md) | Runnable walk-throughs |
| [Changelog](https://github.com/0khacha/the-judge/blob/main/CHANGELOG.md) | Release notes |

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](https://github.com/0khacha/the-judge/blob/main/CONTRIBUTING.md).
A change that affects a verdict needs a regression test that failed before it.

## License

[MIT](https://github.com/0khacha/the-judge/blob/main/LICENSE) © 2026 [@0khacha](https://github.com/0khacha)
