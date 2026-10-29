# C6: cron expression scheduler

Write `cron.py` (project root; standard library only, `datetime` allowed, no third-party cron libraries) with:

* `next_run(expr, after) -> datetime`
* `next_runs(expr, after, count) -> list[datetime]`

## Expression syntax
Five fields separated by any amount of whitespace (leading/trailing whitespace ignored): `minute hour day-of-month month day-of-week`. Ranges: minute 0-59, hour 0-23, day-of-month 1-31, month 1-12, day-of-week 0-7 (both 0 and 7 mean Sunday).

Each field is a comma-separated list of items (an empty item, as in `1,,2` or `1,`, is invalid). An item is:
* `*` : every value of the field's range;
* `N` : a single value;
* `A-B` : an inclusive range (`A <= B`, otherwise invalid);
* any of the above forms `*`, `A-B` followed by `/S` : every S-th value starting at the start of the range (`*/15` in minutes = 0,15,30,45; `*/2` in day-of-month = 1,3,5,...; `10-30/10` = 10,20,30). `N/S` (single value with a step) means `N-max/S` where max is the top of the field's range (`5/20` in minutes = 5,25,45). `S` must be an integer >= 1.
* Numbers are plain decimal digits (leading zeros allowed: `05`). Any out-of-range value or malformed item raises `ValueError`.
* Month and day-of-week fields also accept three-letter English names, case-insensitive: `jan`..`dec`, `sun`..`sat`. Names may be used as single values and as range ends (`mon-fri`, `jan-mar`, `JUL`), also in lists. In the day-of-week field a range may end in 7 (`5-7` = Fri, Sat, Sun). Names with steps are fine (`mon-fri/2` = mon, wed, fri).
* A wrong number of fields raises `ValueError`.

Aliases (the whole expression, lowercase only): `@yearly` and `@annually` = `0 0 1 1 *`, `@monthly` = `0 0 1 * *`, `@weekly` = `0 0 * * 0`, `@daily` and `@midnight` = `0 0 * * *`, `@hourly` = `0 * * * *`. Any other text starting with `@` raises `ValueError`.

## Day matching
A day matches when its month matches and:
* if BOTH the day-of-month field and the day-of-week field are "restricted", the day matches if EITHER of them matches (OR);
* otherwise it must match BOTH (AND).
A field is "restricted" when its text does not start with `*`. So `*/2` and `*` are unrestricted (but `*/2` in day-of-month still only allows the odd days 1,3,5,...), while `1-31` and `0-6` are restricted. Day-of-week uses Sunday = 0 (a Python date has Monday = 0, be careful). Hour, minute and month always have to match.

## `next_run(expr, after)`
* `after` must be a `datetime.datetime` (else `TypeError`) and must be naive (tzinfo `None`, else `ValueError`).
* Returns the earliest datetime strictly later than `after` that matches the expression, with seconds and microseconds equal to 0. So with `after = 10:00:00` and `* * * * *` the answer is 10:01; with `after = 10:15:30` and `*/15 * * * *` the answer is 10:30.
* Months are real calendar months (31st skipped in short months, Feb 29 only in leap years, 2100 is not a leap year).
* If the expression has no match within 3660 days (about ten years) after `after` (for example `0 0 30 2 *`), raise `ValueError`.
* The expression is validated even when it would never match. Errors are raised before any searching.

## `next_runs(expr, after, count)`
The next `count` matches, each strictly after the previous one, as a list. `count` is an int >= 0 (`0` gives `[]`, still validating the expression); a negative count raises `ValueError`.
