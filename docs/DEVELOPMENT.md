# Development Guide

Guide for contributing to The Judge.

## Setup Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/0khacha/the-judge.git
cd the-judge
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
make dev-install
# or
pip install -e ".[dev,visual]"
```

## Project Structure

```
the-judge/
├── the_judge/              # Main package
│   ├── __init__.py        # Public API exports
│   ├── api.py             # Core API functions
│   ├── core/              # Core verification engine
│   │   ├── sandbox.py     # Sandboxed execution
│   │   ├── evidence.py    # Evidence capture
│   │   ├── score_engine.py # Scoring and gates
│   │   ├── critique_engine.py # Adversarial critique
│   │   ├── contract_engine.py # Requirement contracts
│   │   ├── property_engine.py # Dynamic properties
│   │   ├── behavior_engine.py # Behavioral checks
│   │   ├── visual_engine.py   # Visual evaluation
│   │   └── decision.py    # Result data classes
│   └── integrations/      # External integrations
│       ├── cli.py         # CLI interface
│       ├── agent_adapter.py # Agent formatters
│       ├── repair_loop.py # Improvement loop
│       ├── auto_improver.py # Auto-repair
│       ├── audit_trail.py # Audit logging
│       ├── hooks.py       # Git hooks
│       ├── ide.py         # IDE integration
│       ├── watcher.py     # File watcher
│       └── demo.py        # Interactive demo
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── test_*.py         # Integration tests
├── benchmark/            # Adversarial benchmarks
├── examples/             # Usage examples
├── docs/                 # Documentation
└── pyproject.toml        # Package configuration
```

## Development Workflow

### Run Tests

```bash
make test
# or
pytest tests/ -v
```

### Run Tests with Coverage

```bash
make test-cov
# or
pytest tests/ --cov=the_judge --cov-report=html
```

### Run Linters

```bash
make lint
# or
ruff check the_judge/ tests/
mypy the_judge/
```

### Format Code

```bash
make format
# or
ruff format the_judge/ tests/
```

### Verify The Judge Itself

```bash
make verify
# or
judge verify .
```

### Clean Build Artifacts

```bash
make clean
```

## Code Style

We use:
- **Ruff** for linting and formatting (100 char line length)
- **mypy** for type checking
- **pytest** for testing

### Style Guidelines

1. **Type hints**: Use type hints for all function signatures
2. **Docstrings**: Use Google-style docstrings
3. **Line length**: 100 characters maximum
4. **Imports**: Organized (stdlib, third-party, local)
5. **Naming**:
   - Functions/variables: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_CASE`

### Example

```python
from typing import Dict, List, Optional

def verify_workspace(
    workspace: str,
    task_spec: Optional[Dict[str, Any]] = None
) -> VerificationResult:
    """Verify code in a workspace.
    
    Args:
        workspace: Path to workspace directory.
        task_spec: Optional task specification contract.
    
    Returns:
        VerificationResult containing decision and findings.
    
    Raises:
        ValueError: If workspace path is invalid.
    """
    pass
```

## Testing

### Writing Tests

```python
import pytest
from the_judge import verify

def test_verify_pass():
    """Test successful verification."""
    result = verify("examples/simple_cache")
    assert result.decision == "PASS"
    assert result.numeric_score >= 80.0

def test_verify_fail():
    """Test failed verification."""
    result = verify("examples/broken_cache")
    assert result.decision == "FAIL"
    assert len(result.findings) > 0
```

### Test Organization

- `tests/unit/` - Unit tests for individual modules
- `tests/test_*.py` - Integration tests
- `benchmark/` - Adversarial test cases

### Running Specific Tests

```bash
# Run specific test file
pytest tests/test_critique_engine.py -v

# Run specific test function
pytest tests/test_critique_engine.py::test_critique_contradictions -v

# Run tests matching pattern
pytest -k "test_verify" -v
```

## Adding New Features

### 1. Core Engine Features

For changes to `the_judge/core/`:

1. Design the feature (discuss in an issue first)
2. Write tests first (TDD)
3. Implement the feature
4. Update documentation
5. Verify with `judge verify .`

### 2. Integration Features

For changes to `the_judge/integrations/`:

1. Implement the integration
2. Add tests
3. Update relevant docs (INSTALL.md, API.md)
4. Add examples if applicable

### 3. CLI Commands

For new CLI commands in `cli.py`:

1. Add command handler
2. Add tests
3. Update `judge --help` output
4. Update AGENTS.md if agent-relevant

## Documentation

Update these files when making changes:

- **README.md** - High-level overview
- **INSTALL.md** - Installation instructions
- **AGENTS.md** - Agent integration protocol
- **docs/API.md** - Python API reference
- **docs/QUICK_START.md** - Quick start guide
- **CHANGELOG.md** - Version changes

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite: `make test`
4. Verify the project: `make verify`
5. Build: `make build`
6. Tag release: `git tag v1.x.x`
7. Push: `git push --tags`
8. Publish to PyPI: `twine upload dist/*`

## Debugging

### Enable Verbose Output

```bash
judge verify . --debug
```

### Check Evidence Capture

```python
from the_judge.core.evidence import capture_evidence

evidence = capture_evidence(".", task_spec=None)
print(evidence)
```

### Inspect Verification Result

```python
from the_judge import verify
import json

result = verify(".")
print(json.dumps({
    "decision": result.decision,
    "score": result.numeric_score,
    "findings": [f.__dict__ for f in result.findings],
    "trust_profile": result.trust_profile
}, indent=2))
```

## Common Issues

### Import Errors

If you get import errors after changes:

```bash
pip install -e .
```

### Test Failures

If tests fail after changes:

1. Check if you updated the API
2. Update tests accordingly
3. Run `make lint` to check for issues

### Mypy Errors

Add type hints or use `# type: ignore` with comment explaining why.

## Getting Help

- **Issues**: https://github.com/0khacha/the-judge/issues
- **Discussions**: https://github.com/0khacha/the-judge/discussions
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)

## Useful Commands Reference

```bash
make help              # Show all available commands
make install           # Install package
make dev-install       # Install with dev dependencies
make test              # Run tests
make test-cov          # Run tests with coverage
make lint              # Run linters
make format            # Format code
make clean             # Clean build artifacts
make build             # Build distribution
make verify            # Verify the project
make demo              # Run interactive demo
```
