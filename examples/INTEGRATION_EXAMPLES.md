# Integration Examples

Real-world examples of integrating The Judge into different workflows.

## Example 1: Basic Python Library

```python
# example_cache.py
class SimpleCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self.cache = {}
    
    def set(self, key: str, value: any):
        self.cache[key] = value
    
    def get(self, key: str) -> any:
        return self.cache.get(key)
```

```python
# test_cache.py
def test_cache_basic():
    cache = SimpleCache(ttl_seconds=60)
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

```bash
# Verify
judge verify .
# Output: PASS - Score: 85.0 / 100.0
```

## Example 2: With Requirements Contract

```json
// judge.json
{
  "name": "cache-service",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Cache expires entries after TTL",
      "category": "boundary",
      "priority": "critical",
      "properties": ["cache_expiration"]
    },
    {
      "id": "REQ-002",
      "description": "Cache handles concurrent access",
      "category": "concurrency",
      "priority": "high",
      "properties": ["thread_safety"]
    }
  ]
}
```

```python
# Verify with contract
from the_judge import verify
import json

with open("judge.json") as f:
    contract = json.load(f)

result = verify(".", task_spec=contract)
print(f"Decision: {result.decision}")
print(f"Contract coverage: {result.trust_profile.get('specification_coverage')}")
```

## Example 3: Continuous Improvement Loop

```python
# auto_improve.py
from the_judge import improve

def custom_quality_check(workspace, verification):
    """Custom quality evaluator for documentation."""
    # Check if all functions have docstrings
    score = 70  # Base score
    weaknesses = []
    
    # Your custom checks
    if not has_readme():
        weaknesses.append("Missing README.md")
        score -= 20
    
    if not has_docstrings():
        weaknesses.append("Functions lack docstrings")
        score -= 10
    
    return {
        "score": score,
        "passed": score >= 90,
        "weaknesses": weaknesses
    }

result = improve(
    workspace=".",
    quality_evaluator=custom_quality_check,
    agent_command="claude -p --permission-mode acceptEdits",  # who makes the changes
    target_score=90.0,
    max_rounds=5,
)

print(f"Outcome: {result['outcome']} ({result['final_decision']})")
print(f"Final score: {result['quality']['score']}")
print(f"Rounds: {result['total_rounds']}")
```

## Example 4: GitHub Actions Integration

```yaml
# .github/workflows/verify.yml
name: Verify Code Quality

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  verify:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install The Judge
      run: pip install the-judge-verify
    
    - name: Verify Code
      run: judge verify . --json
    
    - name: Upload verification report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: verification-report
        path: .judge_report.json
```

## Example 5: Pre-commit Hook

```bash
# Install hook
judge hook install

# Now commits are blocked if verification fails
git add .
git commit -m "Add new feature"
# Hook runs: judge verify .
# If FAIL: commit is blocked
# If PASS: commit proceeds
```

## Example 6: Custom Repair Function

```python
from the_judge import improve

def smart_repair(workspace, feedback):
    """Custom repair logic: act on the judge's next actions, most important first."""
    changes = []

    for action in feedback["next_actions"]:
        if action["action"] in ("fix_code", "fix_regression"):
            fix_failing_test(workspace, action["test"], action["detail"])
            changes.append(action["test"])
        elif action["action"] == "add_test":
            add_test_from_spec(workspace, action["detail"])  # e.g. "cache.py:45: '>' -> '>='"
            changes.append(action["detail"])

    return {
        "improved": len(changes) > 0,
        "summary": f"Handled {len(changes)} action(s): {', '.join(changes)}",
    }

result = improve(
    workspace=".",
    repair_func=smart_repair,
    max_rounds=3
)
```

## Example 7: Visual Project Evaluation

```python
from the_judge import improve

def visual_quality_evaluator(workspace, verification):
    """Evaluate visual quality of web projects."""
    score = 60
    weaknesses = []
    
    # Check for modern design elements
    if not has_custom_fonts():
        weaknesses.append("Using browser default fonts")
        score -= 10
    
    if not has_responsive_layout():
        weaknesses.append("Layout not responsive")
        score -= 15
    
    if not has_modern_css():
        weaknesses.append("CSS needs modernization")
        score -= 15
    
    return {
        "score": score,
        "passed": score >= 90,
        "weaknesses": weaknesses
    }

result = improve(
    workspace="./website",
    quality_evaluator=visual_quality_evaluator,
    agent_command="auto",  # a known coding agent on PATH makes the changes
    target_score=95.0,
)
```

## Example 8: Multi-file Project

```
project/
├── src/
│   ├── __init__.py
│   ├── cache.py
│   └── utils.py
├── tests/
│   ├── test_cache.py
│   └── test_utils.py
├── judge.json
└── README.md
```

```bash
# Verify entire project
judge verify .

# Verify specific module
judge verify src/cache.py

# Watch mode (re-verify on save)
judge watch .
```

## Example 9: IDE Integration (VS Code)

```bash
# Generate VS Code tasks
judge init vscode

# Now use Command Palette:
# Ctrl+Shift+P -> Tasks: Run Task -> Judge: Verify Workspace
```

`.vscode/tasks.json` is auto-generated with tasks for:
- Verify Workspace
- Improve Workspace
- Contract Coverage
- Watch Mode

## Example 10: Agent Adapter

```python
from the_judge.integrations import AgentAdapter

adapter = AgentAdapter(name="ClaudeCode")

# Verify and get formatted feedback
feedback = adapter.verify_workspace(".")

# Format for AI agent prompt
prompt = adapter.format_agent_prompt_feedback(feedback)

# Send to AI agent
print(prompt)
# Output:
# DECISION: FAIL
# Score: 65.0 / 100.0
# 
# Findings:
# [BEH-001] [HIGH] Behavioral test failed: test_cache_expiration
#   Fix: Review boundary logic in cache.py line 37
```

## See Also

- [API.md](API.md) - Full API reference
- [AGENTS.md](../AGENTS.md) - Agent integration protocol
- [INSTALL.md](../INSTALL.md) - Installation guide
