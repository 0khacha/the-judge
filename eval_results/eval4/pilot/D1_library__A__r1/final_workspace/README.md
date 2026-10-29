# lib - a tiny library lending system

In-memory lending system: books, members, loans, fines, text reports and a small command line.

* `lib.store.Library` - books, members, checkout / return / renew, overdue listing.
* `lib.policy` - per-tier policy. `standard` (default): loan 14 days, limit 3 books, fine 0.25 per late day.
  `premium`: loan 28 days, limit 10 books, fine 0.125 per late day. Tier is set with `add_member(..., tier=...)`
  or `set_tier(...)`. A member whose unpaid fines reach `BLOCK_THRESHOLD` (5.00) cannot check out.
* `lib.fines` - fine calculation. A fine is `late_days * rate`, rounded to cents and never more than the book price.
* `lib.report` - `member_summary` and `overdue_report` text.
* `lib.cli` - `main(argv, lib, out=print)`; commands: `add-book`, `add-member` (with `--tier`), `set-tier`, `checkout`, `return`, `renew`, `summary`, `overdue`.

All dates come from the library clock (`Library(clock=...)`, default `date.today`).
