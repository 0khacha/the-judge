# Recipes

Copy-paste integrations. Every snippet uses the current API ([python-api.md](python-api.md)).

## Start a task test-first

```bash
# 1. write tests from the spec (name each rule's id: def test_expiry():  # R4)
judge freeze .          # 2. freeze them; lists spec rules no test names yet
# 3. implement
judge verify .          # 4. PASS / FAIL / ABSTAIN + numbered next actions
```

Without a freeze or a git commit of the tests before the implementation changed, the
verdict is ABSTAIN with `freeze_tests`: tests written after the code are not
independent evidence.

## GitHub Actions

```yaml
# .github/workflows/judge.yml
name: judge
on: [pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0              # the base branch is needed for --baseline
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install the-judge-verify
      - run: pip install -e .         # your project and its test dependencies
      - run: |
          judge verify . --json --baseline "origin/${{ github.base_ref }}" > judge.json
          code=$?; cat judge.json; exit $code
```

`--baseline` compares the tests with the target branch, so a pull request that deletes,
skips or weakens a test is FAIL, and tests unchanged since the base count as independent
evidence for the implementation the pull request changes.

Exit codes: 0 PASS, 1 FAIL, 2 ABSTAIN, 3 error. To fail the job only on FAIL, end with
`[ $code -ne 1 ]` instead of `exit $code`.

## Block commits that do not pass

```bash
judge hook install            # .git/hooks/pre-commit runs judge verify
judge hook install --pre-push # or on push
judge hook uninstall          # remove
```

## A requirement contract (judge.json)

```json
{
  "name": "cache-service",
  "requirements": [
    {"id": "REQ-001", "description": "Entries expire after ttl seconds",
     "priority": "critical", "tests": ["test_entry_expires_after_ttl"]},
    {"id": "REQ-002", "description": "Missing keys return None",
     "priority": "high", "tests": ["test_missing_key_returns_none"]}
  ]
}
```

`judge verify` loads `judge.json` from the workspace. A requirement is verified by a passing
test listed in `tests`, or one whose name contains the id. An unverified critical
requirement means ABSTAIN. `judge contract .` shows the coverage.

## Let a coding agent fix what the judge finds

```bash
judge improve . --agent                                   # Claude Code, auto-detected
judge improve . --agent "aider --yes-always --message-file {prompt_file}"
judge improve . --agent "my-agent --stdin" --max-rounds 3 --agent-timeout 600
```

## Your own repair step

```python
from the_judge import improve

def repair(workspace: str, feedback: dict) -> dict:
    for action in feedback["next_actions"]:
        if action["action"] in ("fix_code", "fix_regression"):
            ...  # change the implementation so action["test"] passes
        elif action["action"] == "add_test":
            ...  # a planted bug at action["detail"] went unnoticed: add a test from the spec
    return {"improved": True, "summary": "fixed the boundary check"}

result = improve(".", repair_func=repair, max_rounds=4)
print(result["outcome"], result["final_decision"], result["total_rounds"])
```

A runnable version: [examples/agent_loop](../examples/agent_loop/run_agent_loop.py).

## Add your own quality bar

```python
from the_judge import improve

def accessibility(workspace: str, verification: dict) -> dict:
    weaknesses = []
    ...  # run your checker, append descriptions of what is wrong
    return {"score": 100 - 10 * len(weaknesses), "passed": not weaknesses,
            "weaknesses": weaknesses}

result = improve(".", quality_evaluator=accessibility, agent_command="auto", target_score=90)
```

The loop stops only when the verdict is PASS **and** your evaluator passes.

## Feedback text for an agent you call yourself

```python
from the_judge import verify
from the_judge.integrations.agent_runner import build_prompt

result = verify(".")
prompt = build_prompt(result.to_dict())   # verdict, numbered next actions, rules
```

## Editors

```bash
judge init vscode    # tasks: Verify Workspace, Contract Coverage, Watch Mode
judge watch .        # re-verify on every save, any editor
```
