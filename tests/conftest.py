"""Shared test setup.

Tests live in topic folders (verdicts/, evidence/, sandbox/, integrations/, packaging/);
this conftest sits in tests/, so pytest puts tests/ on sys.path and every folder can
`from audit_helpers import ...`.
"""
