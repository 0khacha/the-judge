# Claims under test (from the published README and AGENTS.md of the-judge-verify 1.0.0)

1. It turns a one-shot builder into an improver: "Build -> Verify -> Critique -> Improve -> Re-verify -> Repeat" until the code reaches production quality (README "What it does").
2. Agent loop (AGENTS.md): after each change run `judge verify . --json`; PASS -> done; FAIL -> fix using `findings[].suggested_focus` and re-verify; ABSTAIN -> write independent tests and re-verify; stop after 5 repair rounds.
3. It catches defects the agent's own claims and visible tests miss (README example: hidden TTL off-by-one -> FAIL with a pointer to the bug).
4. Its verdicts are trustworthy: PASS means behaviour verified, FAIL means real defects (exit codes 0/1/2/3 = PASS/FAIL/ABSTAIN/ERROR), and ABSTAIN when evidence is insufficient instead of a misleading verdict.
5. It resists gaming: skipped/vacuous tests are not evidence, and in a git repo deleted tests, removed assertions and added skips relative to HEAD are tampering that blocks PASS; collection tampering is detected.

Derived hypotheses:
- H1 (claims 1-3): condition B (agent + judge loop) has a higher hidden-test pass rate than A (one-shot), by more than run-to-run variance.
- H2 (claim 2): iterations in B fix real (hidden-test) bugs, not only visible tests.
- H3 (claim 4): on known-correct code no FAIL; on subtly broken code no PASS; broken environment -> ABSTAIN.
- H4 (claim 5): hard-coded outputs, deleted/skipped tests and collection edits are detected.
