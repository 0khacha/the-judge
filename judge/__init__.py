"""
Backward compatibility package shim for legacy code importing `judge`.
Redirects all imports to `the_judge`.
"""
from the_judge import (
    verify,
    verify_workspace,
    improve,
    VerificationResult,
    Finding,
)

__version__ = "1.0.0"

__all__ = [
    "verify",
    "verify_workspace",
    "improve",
    "VerificationResult",
    "Finding",
]
