# Ticket: composite keys and "keep last" de-duplication

Two requests from the data team: records are unique per (region, id), not per id alone, and when a feed repeats a record the *latest* one is the correct one.

1. `pipeline.run(text, schema, key=None, keep="first")`. `key` may now be a single field name (as before) or a list/tuple of field names (composite key). An empty list/tuple means no key. Every key field must exist in the schema (`EtlError("unknown key field <name>")`) and be required (`EtlError("key field <name> must be required")`). `keep` must be `"first"` or `"last"`, otherwise `EtlError`.
2. Two accepted rows are duplicates when all key values are equal *after coercion* (so `01` and `1` are the same `int` key).
   * `keep="first"`: the first row stays and every later one is rejected with `line N: duplicate of line M` (M = line of the row that stays), as today.
   * `keep="last"`: the last row of a group stays; every earlier row is rejected with `line N: superseded by line M`, where M is the line of the *next* row with the same key (so a group of three has two rejects, each naming its successor).
3. Only valid rows take part in de-duplication. A row rejected for a coercion problem (or wrong field count) never counts as a duplicate and never supersedes anything, and it does not claim a key either (under `keep="first"` a later valid row with the same key is accepted).
4. Without a key the rows keep file order and nothing is de-duplicated (also for `keep="last"`). With a key the accepted rows are sorted by the key tuple (in the order of the names given, comparing coerced values); `Result.lines` stays aligned with `Result.rows`.
5. `Result.stats` gets a new entry `"superseded"` (rows removed under `keep="last"`, always 0 for `keep="first"`). `"duplicates"` counts every row removed as a duplicate or superseded; `"rejected"` still counts all rejects (invalid, duplicate and superseded). `Result.rejects` stays sorted by line; a superseded reject carries the line of the superseded row.
6. CLI: `--key` takes a comma separated list (`--key region,id`), new option `--keep first|last` (default `first`); bad values print `error: ...` and return 1 like other errors. The summary line becomes `read=<n> accepted=<n> rejected=<n> duplicates=<n> superseded=<n>`.

Single-name keys with the default `keep="first"` must behave exactly as before; everything else (reading, coercion messages, writers, CLI output after the summary) stays the same.
