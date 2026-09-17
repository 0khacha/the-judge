# Python API Reference

Complete Python API documentation for The Judge.

## Core Functions

### `verify()`

Verify code against behavioral contracts and quality gates.

```python
from the_judge import verify

result = verify(
    workspace=".",
    task_spec=None,
    previous_evidence=None
)

print(result.decision)        # "PASS", "FAIL", or "ABSTAIN"
print(result.numeric_score)   # 0.0 to 100.0
print(result.findings)        # List[Finding]
```

**Parameters:**

- `workspace` (str): Path to directory or Python file to verify
- `task_spec` (Optional[Dict]): Task specification contract (see [Contracts](#contracts))
- `previous_evidence` (Optional[Dict]): Previous evidence for regression tracking

**Returns:** `VerificationResult`

---

### `improve()`

Run continuous improvement loop until code reaches quality threshold.

```python
from the_judge import improve

result = improve(
    workspace=".",
    repair_func=None,
    max_rounds=5,
    target_score=90.0,
    task_spec=None,
    quality_evaluator=None,
    require_evidence_sufficiency=True
)

print(result["final_decision"])
print(result["rounds"])
print(result["score_progression"])
```

**Parameters:**

- `workspace` (str): Path to workspace
- `repair_func` (Optional[Callable]): Custom repair function
- `max_rounds` (int): Maximum improvement rounds (default: 5)
- `target_score` (float): Target quality score 0-100 (default: 90.0)
- `task_spec` (Optional[Dict]): Task contract
- `quality_evaluator` (Optional[Callable]): Custom quality evaluator
- `require_evidence_sufficiency` (bool): Continue if evidence insufficient (default: True)

**Returns:** Dict with multi-round history and final verdict

---

### `critique()`

Run adversarial critique to identify weaknesses and unverified assumptions.

```python
from the_judge import critique

result = critique(
    workspace=".",
    task_spec=None,
    previous_round=None
)

print(result.findings)
print(result.evidence_sufficiency)
print(result.contradictions)
```

**Parameters:**

- `workspace` (str): Path to workspace
- `task_spec` (Optional[Dict]): Task contract
- `previous_round` (Optional[Dict]): Previous round for comparison

**Returns:** `CritiqueResult`

---

## Data Classes

### `VerificationResult`

```python
@dataclass
class VerificationResult:
    decision: str                    # "PASS", "FAIL", "ABSTAIN"
    numeric_score: float             # 0.0 to 100.0
    trust_profile: Dict[str, Any]    # Evidence coverage data
    findings: List[Finding]          # Structured findings
    provenance: Dict[str, Any]       # Verification metadata
    blocking_issues: List[str]       # Critical issues
    insufficient_notes: List[str]    # Evidence gaps
    runtime_seconds: float           # Execution time
```

### `Finding`

```python
@dataclass
class Finding:
    id: str                          # e.g., "BEH-001"
    category: str                    # "behavior", "security", etc.
    severity: str                    # "low", "medium", "high", "blocking"
    description: str                 # Human-readable description
    property_name: Optional[str]     # Related property/test
    observed: Optional[str]          # What was observed
    expected: Optional[str]          # What was expected
    suggested_focus: str             # Actionable guidance
```

---

## Integration Classes

### `AgentRepairLoop`

Multi-round repair loop for autonomous improvement.

```python
from the_judge.integrations import AgentRepairLoop

def my_repair_func(workspace, feedback):
    # Your repair logic
    # feedback contains: verification result, findings, critique
    return {"changed": True, "description": "Fixed issues"}

loop = AgentRepairLoop(
    max_rounds=5,
    quality_threshold=90.0,
    quality_evaluator=custom_evaluator,  # Optional
    require_evidence_sufficiency=True
)

result = loop.run_repair_loop(
    workspace=".",
    agent_repair_func=my_repair_func,
    task_spec=None
)
```

### `AgentAdapter`

Format verification output for different AI agents.

```python
from the_judge.integrations import AgentAdapter

adapter = AgentAdapter(name="MyAgent")

# Verify and get formatted feedback
feedback = adapter.verify_workspace(".")

# Format for agent prompt
prompt = adapter.format_agent_prompt_feedback(feedback)
```

### `AutoImprover`

Built-in automatic improvement engine.

```python
from the_judge.integrations import AutoImprover

improver = AutoImprover(workspace=".")

feedback = {
    "verification": verify_result,
    "critique": critique_result
}

result = improver.improve_workspace(feedback)
```

---

## Contracts

Define requirements in `judge.json`:

```json
{
  "name": "my-project",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "Cache expires after TTL seconds",
      "category": "boundary",
      "priority": "critical",
      "properties": ["cache_expiration"]
    }
  ]
}
```

Load and use:

```python
import json
from the_judge import verify

with open("judge.json") as f:
    task_spec = json.load(f)

result = verify(".", task_spec=task_spec)
```

---

## Quality Evaluators

Custom quality evaluators for domain-specific checks:

```python
def accessibility_evaluator(workspace, verification):
    """Check accessibility requirements."""
    return {
        "score": 85,
        "passed": False,
        "weaknesses": [
            "Missing alt text on images",
            "Insufficient color contrast"
        ]
    }

result = improve(
    workspace=".",
    quality_evaluator=accessibility_evaluator,
    target_score=95.0
)
```

---

## CLI Equivalents

| CLI Command | Python API |
|-------------|------------|
| `judge verify .` | `verify(".")` |
| `judge improve .` | `improve(".")` |
| `judge contract .` | Load contract via `task_spec` |

---

## Error Handling

```python
from the_judge import verify

try:
    result = verify(".")
    
    if result.decision == "FAIL":
        for finding in result.findings:
            print(f"{finding.id}: {finding.description}")
            print(f"Fix: {finding.suggested_focus}")
    
    elif result.decision == "ABSTAIN":
        print("Insufficient evidence:")
        for note in result.insufficient_notes:
            print(f"- {note}")
    
    else:  # PASS
        print(f"Success! Score: {result.numeric_score}")
        
except Exception as e:
    print(f"Verification error: {e}")
```

---

## Advanced Usage

### Regression Tracking

```python
# Round 1
result1 = verify(".")
evidence1 = result1.provenance

# Round 2 - track regressions
result2 = verify(".", previous_evidence=evidence1)

# Check for regressions
for issue in result2.blocking_issues:
    if "REGRESSION" in issue:
        print(f"Regression detected: {issue}")
```

### Visual Project Evaluation

```python
from the_judge import improve

def visual_quality_evaluator(workspace, verification):
    """Evaluate visual quality of web projects."""
    # Your visual analysis logic
    return {
        "score": 75,
        "passed": False,
        "weaknesses": [
            "Typography needs refinement",
            "Spacing inconsistent"
        ]
    }

result = improve(
    workspace=".",
    quality_evaluator=visual_quality_evaluator,
    target_score=95.0
)
```

---

## See Also

- [AGENTS.md](../AGENTS.md) - Agent integration protocol
- [INSTALL.md](../INSTALL.md) - Installation guide
- [architecture.md](architecture.md) - System architecture
