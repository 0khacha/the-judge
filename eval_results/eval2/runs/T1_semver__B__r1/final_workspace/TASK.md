# T1: semver comparison

Create `semver.py` with:

- `compare(a, b)` -> `-1`, `0` or `1` comparing two semantic version strings `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`.
- `sort_versions(versions)` -> new list sorted ascending by precedence (stable: versions of equal precedence keep input order).

Rules (semver 2.0.0 precedence):
1. MAJOR, MINOR, PATCH are compared numerically.
2. A version with a prerelease has LOWER precedence than the same version without one.
3. Prerelease is dot-separated identifiers, compared left to right: identifiers consisting only of digits are compared numerically; other identifiers are compared lexically in ASCII order; a numeric identifier is lower than a non-numeric one; if all shared identifiers are equal, the one with fewer identifiers is lower.
4. Build metadata (after `+`) is ignored entirely: `1.0.0+a` and `1.0.0+b` compare equal (0).
5. Invalid input (not exactly three numeric core parts, empty prerelease identifier, non-string) raises `ValueError`.
