# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via:
- **Email**: Create an issue and request private disclosure
- **GitHub Security Advisories**: Use the "Security" tab

Include:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

## Security Model

The Judge operates with the following security boundaries:

### Trusted Components

- The Judge verification engine itself
- User's own code being verified
- Tests written by the user

### Untrusted Components

- External packages under test
- Generated code from AI agents
- Third-party dependencies (isolated)

### Isolation Mechanisms

**The sandbox is not a security boundary.** It exists to keep the verdict honest
against careless or lazy code, not to contain hostile code. Only run code you would
be willing to run on your own machine.

1. **Separate process**: tests run in a `python -m pytest` subprocess with stdin closed
   and a timeout.
2. **Collection outside the workspace**: test files (the workspace's and the judge's
   probes) are copied into a temporary directory with a randomized name and collected
   there, so a workspace `conftest.py` at the root cannot silently rewrite collection
   of the judge's probes. The subprocess runs with the workspace as its working
   directory, like a normal `pytest` run, so relative paths in tests work and the
   working directory does not reveal the sandbox.
3. **Tampering detection**: SHA-256 check of the copied test files after the run; a
   manifest of expected test names (missing or deselected tests are a FAIL); and, in a
   git repository, a comparison of the tests against `HEAD` or `--baseline REF`
   (deleted tests, removed assertions, added skips are a FAIL).
4. **Environment scrubbing**: `JUDGE_*`, `BENCHMARK_*` and `PYTEST_CURRENT_TEST`
   variables are removed; only a small allow-list of variables is passed through.

### Isolation Limitations

1. **Detectable**: code can still tell it is under test (pytest is imported, the test
   files live in a temporary directory, the environment is reduced). Randomized names
   only remove the cheapest hint (the former fixed `t_` directory prefix).
2. **Filesystem**: the workspace is the working directory and is on `PYTHONPATH`;
   tests can read and write it, and anything else the user can.
3. **Network and resources**: no network isolation, no memory/CPU limits beyond the
   timeout.
4. **Target self-modification**: source changes made by the code during the run are
   not detected.

### What The Judge Does NOT Protect Against

- Malicious code with kernel-level exploits
- Network-based attacks during test execution
- Resource exhaustion (memory, CPU) - user responsibility
- Social engineering

## Best Practices

1. **Review AI-generated code** before running verification
2. **Pin dependencies** in your requirements
3. **Use virtual environments** for isolation
4. **Limit test execution time** in CI/CD
5. **Monitor resource usage** during verification

## Known Limitations

- Sandbox isolation is subprocess-level, not container/VM-level
- No protection against infinite loops or fork bombs
- Network access available during test execution
- File system access within workspace

## Vulnerability Disclosure Timeline

1. **Day 0**: Report received
2. **Day 1-2**: Acknowledge receipt
3. **Day 3-7**: Initial assessment
4. **Day 7-30**: Develop and test fix
5. **Day 30**: Public disclosure + patch release

## Security Updates

Security patches are released as:
- Patch version bumps (1.0.x → 1.0.y)
- Documented in CHANGELOG.md
- Announced in GitHub releases

## Contact

For security concerns: Open a GitHub issue requesting private disclosure.

## Acknowledgments

We appreciate responsible disclosure from security researchers.
