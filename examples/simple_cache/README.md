# Simple Cache Example

A minimal example demonstrating The Judge verification on a simple cache implementation.

## Structure

```
simple_cache/
├── cache.py           # Simple cache implementation
├── test_cache.py      # Test suite
├── judge.json         # Requirement contract
└── README.md          # This file
```

## Running Verification

```bash
# From this directory
judge verify .

# Or from project root
judge verify examples/simple_cache/
```

## Expected Output

```
DECISION: PASS
Score: 95.0 / 100.0

Evidence:
- 6 behavioral tests passed
- All critical requirements verified
- No security issues detected

Contract Coverage:
- REQ-001: cache_expiration ✓
- REQ-002: missing_key_handling ✓
- REQ-003: clear_operation ✓
```

## Using with Improvement Loop

```bash
judge improve .
```

This will run multiple rounds of evaluation and improvement until the code reaches a quality score of 90+.

## Python API

```python
from the_judge import verify
import json

# Load contract
with open("judge.json") as f:
    contract = json.load(f)

# Verify with contract
result = verify(".", task_spec=contract)

print(f"Decision: {result.decision}")
print(f"Score: {result.numeric_score}")

for finding in result.findings:
    print(f"- {finding.id}: {finding.description}")
```
