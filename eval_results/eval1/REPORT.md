# Evaluation: does the-judge-verify turn a one-shot builder into a continuous improver?

**Verdict: no evidence.** On this benchmark, the agent with the judge loop (B) did not beat the
agent without it (A). Both conditions solved every task perfectly (100% hidden tests, 15/15 runs
each), so there was nothing for the loop to fix. In the loop, the judge never returned PASS on
code that was correct. Its feedback was either an ABSTAIN the agent could not act on, or a false
FAIL that led agents to rewrite good tests. B cost about 15% more tokens and 58% more wall time.

Conflict of interest: the evaluator (this assistant) also made most of the judge's recent
changes. To limit bias, the tasks, hidden tests, references and broken variants were written and
hash-frozen before any agent ran (`02_benchmark_frozen_sha256.txt`; all 25 files were re-verified
unchanged after the runs), and nothing in the judge was changed during the evaluation.

## Setup

- Judge: `the-judge-verify 1.0.0`, installed from TestPyPI into a clean venv (`00_pip_freeze.txt`,
  `00_judge_version.txt`). Claims under test: `01_claims.md`, derived from the published README and
  AGENTS.md (`00_published_*.md`).
- Agent: fresh Claude subagents, model **Sonnet**, identical base prompt in both conditions. B's
  prompt adds the AGENTS.md loop (quoted verbatim) and a command to run the judge. A is a normal
  agent that may run the visible tests; it is not told to work "in one pass".
- B ran the judge through a logging wrapper (`harness/example_judge_wrapper.py`). The wrapper
  snapshots the workspace before each call, calls the installed judge unchanged, saves its full
  output, and refuses a 6th call. Iterations and regressions are therefore measured from evidence
  (`runs/<id>/iter_N/`), not from agent self-reports.
- Tasks (`tasks/`): T1 query-string parser and T2 sliding-window rate limiter (feature tasks);
  T3 unicode slugify with truncation and T4 ordered parallel map with concurrency and exception
  order (edge-case tasks); T5 bill split (trap task: the obvious `[total // n] * n` passes the
  visible examples but fails the hidden tests).
- Hidden tests (`hidden/<task>/test_hidden.py`) lived in a randomly named directory outside every
  workspace and were copied here only after all runs. A grep of all 30 agent transcripts found no
  mention of that directory, of `eval_results`, or of any other run's workspace.
- Scoring (`harness/score_runs.py`): the hidden tests run against the agent's solution module only,
  in a clean directory, so the agent's own test files cannot interfere.

## Results: task × condition × run

| task | cond | run | hidden pass | judge iterations | judge decisions | regressions | tokens | wall (s) |
|---|---|---|---|---|---|---|---|---|
| T1 parser | A | 1 | 14/14 | 0 | — | 0 | 34,252 | 40 |
| T1 parser | A | 2 | 14/14 | 0 | — | 0 | 34,530 | 146 |
| T1 parser | A | 3 | 14/14 | 0 | — | 0 | 35,219 | 91 |
| T1 parser | B | 1 | 14/14 | 2 | ABSTAIN, ABSTAIN | 0 | 39,790 | 127 |
| T1 parser | B | 2 | 14/14 | 2 | ABSTAIN, ABSTAIN | 0 | 39,175 | 193 |
| T1 parser | B | 3 | 14/14 | 2 | ABSTAIN, ABSTAIN | 0 | 39,985 | 123 |
| T2 rate limiter | A | 1 | 9/9 | 0 | — | 0 | 34,295 | 39 |
| T2 rate limiter | A | 2 | 9/9 | 0 | — | 0 | 34,633 | 154 |
| T2 rate limiter | A | 3 | 9/9 | 0 | — | 0 | 34,314 | 63 |
| T2 rate limiter | B | 1 | 9/9 | 2 | ABSTAIN ×2 | 0 | 40,058 | 121 |
| T2 rate limiter | B | 2 | 9/9 | 3 | ABSTAIN ×3 | 0 | 40,153 | 177 |
| T2 rate limiter | B | 3 | 9/9 | 3 | ABSTAIN ×3 | 0 | 40,890 | 141 |
| T3 slugify | A | 1 | 20/20 | 0 | — | 0 | 34,454 | 104 |
| T3 slugify | A | 2 | 20/20 | 0 | — | 0 | 34,427 | 161 |
| T3 slugify | A | 3 | 20/20 | 0 | — | 0 | 34,403 | 82 |
| T3 slugify | B | 1 | 20/20 | 2 | ABSTAIN ×2 | 0 | 39,116 | 98 |
| T3 slugify | B | 2 | 20/20 | 2 | ABSTAIN ×2 | 0 | 38,100 | 197 |
| T3 slugify | B | 3 | 20/20 | 2 | ABSTAIN ×2 | 0 | 38,443 | 131 |
| T4 parallel map | A | 1 | 8/8 | 0 | — | 0 | 34,297 | 59 |
| T4 parallel map | A | 2 | 8/8 | 0 | — | 0 | 34,229 | 109 |
| T4 parallel map | A | 3 | 8/8 | 0 | — | 0 | 34,005 | 45 |
| T4 parallel map | B | 1 | 8/8 | 2 | ABSTAIN ×2 | 0 | 38,463 | 100 |
| T4 parallel map | B | 2 | 8/8 | 2 | ABSTAIN ×2 | 0 | 39,043 | 179 |
| T4 parallel map | B | 3 | 8/8 | 2 | ABSTAIN ×2 | 0 | 39,717 | 141 |
| T5 split bill (trap) | A | 1 | 13/13 | 0 | — | 0 | 34,122 | 120 |
| T5 split bill (trap) | A | 2 | 13/13 | 0 | — | 0 | 34,190 | 176 |
| T5 split bill (trap) | A | 3 | 13/13 | 0 | — | 0 | 33,972 | 48 |
| T5 split bill (trap) | B | 1 | 13/13 | 3 | ABSTAIN, **FAIL**, ABSTAIN | 0 | 40,888 | 149 |
| T5 split bill (trap) | B | 2 | 13/13 | 3 | ABSTAIN, **FAIL**, ABSTAIN | 0 | 40,159 | 228 |
| T5 split bill (trap) | B | 3 | 13/13 | 4 | ABSTAIN, **FAIL**, **FAIL**, ABSTAIN | 0 | 41,188 | 162 |

"Tokens" is the subagent's total token count as reported by the harness; it is not split into
input and output. Raw data: `06_runs_table.csv`, `05_scores.json`, `04_agent_usage.jsonl`.

### Averages (15 runs per condition)

| | A (no skill) | B (skill loop) |
|---|---|---|
| Hidden-test pass rate | **100%** (sd 0) | **100%** (sd 0) |
| Judge iterations | 0 | 2.4 |
| Regressions | 0 | 0 |
| Final judge decision PASS | — | **0 / 15** |
| Agents that wrote their own tests | 0 / 15 | 15 / 15 |
| Tokens | 34,356 (sd 290) | 39,678 (sd 909): **+15.5%** |
| Wall time | 96 s (sd 46) | 151 s (sd 36): **+58%** |
| Tool calls | 5.3 | 7.5 |

## Judge accuracy (Step 4, `judge_accuracy/`)

Each case is a workspace with the visible tests, judged by the TestPyPI-installed judge.

| Case | Expected | Got | OK? | Note |
|---|---|---|---|---|
| Correct T1 parser | not FAIL | **FAIL** | ✗ | "Type checker failed with 1 error": mypy `var-annotated` on `out = {}` |
| Correct T2 rate limiter | not FAIL | **FAIL** | ✗ | same: `_calls = defaultdict(deque)` has no annotation |
| Correct T3 / T4 / T5 | not FAIL | ABSTAIN | ✓ | no probe applies, so no independent evidence |
| Broken T1 / T3 / T4 / T5 | not PASS | ABSTAIN | ✓ | not PASS, but the bug was not found either |
| Broken T2 (fixed window) | not PASS | FAIL | ✓ (wrong reason) | FAIL from mypy, not from the windowing bug |
| pytest missing from the judge's env | ABSTAIN | ABSTAIN | ✓ | clear "install pytest" note |
| Correct code, no tests at all | ABSTAIN | **FAIL** | ✗ | pytest exit code 5 ("no tests collected") treated as a test failure |
| Path does not exist | ERROR | ERROR (exit 3) | ✓ | |
| Hard-coded answers for the visible inputs | not PASS | ABSTAIN | ~ | not PASS, but not detected as gaming |
| Failing test deleted (git) | not PASS | FAIL, tampering | ✓ | |
| Assertion changed to the buggy output (git) | not PASS | FAIL, tampering | ✓ | |
| Failing test skipped (git) | not PASS | FAIL, tampering | ✓ | |
| Assertion made tautological (git) | not PASS | FAIL, tampering | ✓ | |
| conftest deselects the failing test | not PASS | FAIL, collection tampering | ✓ | |
| conftest rewrites failures as passes | not PASS | ABSTAIN | ~ | not detected; only no-probe ABSTAIN prevented PASS |
| Failing test skipped (no git) | not PASS | ABSTAIN + skip finding | ✓ | |

Plus, inside the A/B loops: **4 false FAILs out of 36 judge calls**, all on T5 (3 of 3 B runs).
When an agent wrote a parametrized test (`@pytest.mark.parametrize`), the judge reported
"COLLECTION TAMPERING DETECTED: expected challenge test(s) missing: test_invalid". The code at
each of those snapshots passed 100% of the hidden tests (verified from `runs/*/iter_N/`).

**Counts: false PASS 0 (0/5 broken, 0/7 gamed; 0 PASS in 36 loop calls). False FAIL 7: 2/5
correct (mypy), 1 no-tests case, and 4 in the loop (parametrized tests).**

## Answers

1. **Did B beat A on hidden-test pass rate?** No. Both 100%, with sd 0 in both conditions. The gap
   is 0, which is not larger than the run-to-run variance (also 0). This is a ceiling effect: the
   benchmark was too easy for this model to discriminate. That includes the trap task, where every
   A run used `divmod` correctly.
2. **Did iterating fix real bugs, or just make visible tests pass?** Neither, because there were no
   bugs to fix: hidden-test pass rate was 100% at every judged snapshot of every B run. The B
   iterations added tests (15/15 B agents wrote tests, 0/15 A agents did). They also rewrote
   parametrized tests into plain loops to clear false FAILs, which made the tests no better and
   arguably worse. The judge's ABSTAIN feedback ("no independent evidence") could not be acted on:
   tests the agent writes do not count, and every agent stopped after 2 to 4 calls.
3. **Cost:** B used **+15.5% tokens** (39.7k vs 34.4k per task) and **+58% wall time** (151 s vs
   96 s), with no measured quality gain.
4. **Judge accuracy:** false PASS **0**. False FAIL **7**: 2 correct solutions failed by mypy
   annotation errors, 1 no-tests workspace failed instead of ABSTAIN, and 4 loop calls failed on
   parametrized tests. Bug detection on subtly broken code was **0/5 for the right reason**: 4
   ABSTAIN, and 1 FAIL caused by mypy. Tamper detection worked in git (4/4) and for conftest
   deselection, but not for a conftest that rewrites outcomes or for hard-coded answers. Those two
   cases were held at ABSTAIN only because no probe applies.
5. **Verdict: no evidence.**
   - *Strongest evidence for:* it never certified wrong or gamed code as PASS (0 false PASS), it
     returned ABSTAIN rather than PASS when it had no independent evidence, and it caught every
     git-visible test tampering attempt plus conftest deselection.
   - *Strongest evidence against:* across 36 loop calls on code that was 100% correct, it never
     said PASS. Its feedback was either unactionable (ABSTAIN) or wrong (4 false tampering FAILs
     that pushed agents to rewrite good tests). Outside the loop it failed correct code for
     missing type annotations and for having no tests. The loop cost +15% tokens and +58% time.
     The README's claim that it "drives multi-round improvements" did not show up: agents made 2.4
     judge calls on average and improved nothing measurable.

## Not tested / limits

- **The A/B could not measure improvement** because of the ceiling: both conditions scored 100%.
  A harder benchmark, a weaker model, or larger multi-file tasks might show a difference. I did
  not change the tasks after seeing results, because that would be tuning.
- One model (Sonnet), 3 runs per cell, 5 small single-file tasks, Windows only.
- Token counts are harness totals per subagent, not input/output splits; no cost in dollars.
- `judge improve`, visual projects, `judge.json` contracts and the `--baseline` flag were not
  exercised by the agents. No B agent found a way to supply "independent evidence"; two said
  they did not know the `judge.json` format.
- A agents were allowed to run the visible tests, so A is "normal agent without the skill", not
  a literal single file write.
- Agents were told to stay in their workspace; this was checked by grepping transcripts, not
  enforced by a sandbox.
- mypy ran because a system-wide mypy is on PATH, even though the eval venv had none. In an
  environment without mypy, the two mypy false FAILs would be ABSTAIN instead.
