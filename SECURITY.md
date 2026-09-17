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

1. **Sandbox Execution**: Tests run in subprocess isolation
2. **Tampering Detection**: Monitors for conftest hijacking, sys.modules manipulation
3. **Anonymous Execution**: Strips process markers
4. **TOCTOU Protection**: Detects time-of-check-time-of-use symlink attacks

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
