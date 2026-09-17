# Contributing to The Judge

Thank you for your interest in contributing to The Judge! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and professional. We're here to build quality tools together.

## How to Contribute

### 1. Report Bugs

Use [GitHub Issues](https://github.com/0khacha/the-judge/issues) with the bug report template:

- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, The Judge version)
- Relevant logs or output

### 2. Suggest Features

Use [GitHub Issues](https://github.com/0khacha/the-judge/issues) with the feature request template:

- Clear description of the feature
- Use case and problem it solves
- Proposed solution
- Alternatives considered

### 3. Submit Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-feature`
3. **Make your changes**
4. **Write tests** for your changes
5. **Run the test suite**: `make test`
6. **Run linters**: `make lint`
7. **Format code**: `make format`
8. **Verify the project**: `make verify`
9. **Commit with clear messages**
10. **Push and create a pull request**

## Development Setup

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development instructions.

Quick setup:

```bash
# Clone the repository
git clone https://github.com/0khacha/the-judge.git
cd the-judge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
make dev-install

# Run tests
make test

# Run linters
make lint
```

## Code Style

- **Line length**: 100 characters
- **Formatter**: Ruff
- **Linter**: Ruff + mypy
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all public APIs

Example:

```python
from typing import Optional

def verify_workspace(
    workspace: str,
    task_spec: Optional[dict] = None
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

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Test both success and failure cases

```python
def test_verify_pass():
    """Test successful verification."""
    result = verify("examples/simple_cache")
    assert result.decision == "PASS"

def test_verify_fail_on_broken_code():
    """Test verification fails on broken code."""
    result = verify("examples/broken_cache")
    assert result.decision == "FAIL"
    assert len(result.findings) > 0
```

## Commit Messages

Use clear, descriptive commit messages:

```
type: brief description

Longer explanation if needed.

- Details
- More details
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Maintenance tasks

Examples:
```
feat: add visual quality evaluator for web projects

fix: handle edge case in cache expiration logic

docs: add examples for custom quality evaluators

refactor: simplify evidence capture pipeline

test: add regression tests for boundary conditions
```

## Pull Request Guidelines

1. **One feature per PR** - Keep PRs focused
2. **Update documentation** - If you change APIs, update docs
3. **Add tests** - No PR without tests (unless docs-only)
4. **Update CHANGELOG.md** - Add entry for your change
5. **Pass CI checks** - All tests and lints must pass
6. **Verify with The Judge** - Run `make verify` before submitting

### PR Description Template

```markdown
## Description
Brief description of changes.

## Motivation
Why is this change needed?

## Changes
- List of changes
- Another change

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Code formatted (`make format`)
- [ ] Linters pass (`make lint`)
- [ ] Tests pass (`make test`)
- [ ] Verification passes (`make verify`)
```

## Areas for Contribution

### High Priority

- Additional integration examples
- Performance optimizations
- Documentation improvements
- Bug fixes

### Medium Priority

- New IDE integrations (JetBrains, etc.)
- Additional quality evaluators (security, accessibility)
- Enhanced visual evaluation engine
- Better error messages

### Ideas Welcome

- New features (discuss in an issue first)
- Architecture improvements
- Better test coverage
- Usability enhancements

## What NOT to Contribute

- Breaking changes without discussion
- Features that don't fit the core mission
- Code without tests
- Poorly documented code
- Code that doesn't pass linters

## Questions?

- **Issues**: [GitHub Issues](https://github.com/0khacha/the-judge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0khacha/the-judge/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes
- Project documentation (for significant contributions)

Thank you for contributing to The Judge!
