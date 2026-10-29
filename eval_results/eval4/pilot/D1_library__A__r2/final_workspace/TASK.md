# Ticket: premium membership tier

Some members pay for a premium membership. Add a membership tier to the lending system.

Requirements

1. Every member has a `tier`, either `"standard"` (the default) or `"premium"`. `Library.add_member(name, tier="standard")` takes the tier. Any other tier value raises `ValueError` and no member is created.
2. Loan period: standard 14 days (as today), premium 28 days. This applies to the due date set by `checkout` and to the extension granted by `renew` (renew adds one loan period of the member's *current* tier).
3. Loan limit: standard 3 (as today), premium 10. `LimitError` is raised beyond the limit.
4. Fine rate per late day: standard 0.25 (as today), premium 0.125. The fine is still rounded to cents and capped at the book price. The rate used is the one of the member's tier at the time the fine is computed (return time, or the moment `overdue_report` is generated).
5. New method `Library.set_tier(member_id, tier)` changes a member's tier and returns the member. Invalid tier: `ValueError` (tier unchanged). Unknown member: `KeyError`. Loans that are already open keep their due date; the new tier only affects later checkouts, renewals, limits and fines.
6. `report.member_summary` gets a line `Tier: <tier>` directly after the first line (`Member #..`), and the "Active loans" line shows the member's own limit (for example `2/10` for a premium member).
7. `report.overdue_report` shows the fine according to the member's tier rate.
8. Command line: `add-member NAME [--tier TIER]` (prints `member <id> <name>` as before; bad tier gives `error: ...` and exit code 1) and a new command `set-tier ID TIER` that prints `member <id> tier <tier>` (errors give `error: ...` and exit code 1).

Everything else must keep working as it does today (fine blocking at 5.00 owed, renewal rules, overdue ordering, reports, CLI usage and error handling).
