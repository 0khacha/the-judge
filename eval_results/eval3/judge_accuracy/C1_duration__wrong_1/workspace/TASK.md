# C1: duration parsing and formatting

Write `duration.py` (in the project root) with two functions.

## `parse_duration(text) -> int`
Parses a human duration into a whole number of seconds.

* Units: `w` = 604800 s, `d` = 86400, `h` = 3600, `m` = 60, `s` = 1. Unit letters are case-insensitive (`1H30M` is fine).
* A duration is one or more components `<number><unit>`, e.g. `1h30m`. Whitespace (spaces, tabs) is allowed between components (`1h 30m`) and around the whole string, but NOT between a number and its unit (`1 h` is invalid) and not between a leading `-` and the rest.
* Units must appear in strictly descending order (w, d, h, m, s), each at most once. `30m1h` and `1h1h` are invalid.
* A bare number without a unit (`90`) is invalid. An empty or whitespace-only string is invalid. Unknown units are invalid.
* Numbers use ASCII digits 0-9 only. A number may have a fractional part (`1.5h`) written as digits `.` digits (`.5h` and `1.h` are invalid). A fraction is allowed only in the LAST component: `1.5h30m` and `1.5m 30s` are invalid.
* The total is rounded to a whole second: halves round up (away from zero), so `0.5s` -> 1, `1.5s` -> 2, `2.5s` -> 3, `0.4s` -> 0. Do not use banker's rounding.
* A single leading `-` makes the total negative (`-1h30m` -> -5400). Rounding is applied to the absolute value, so `-0.5s` -> -1. No `+` sign.
* The result is an `int`.
* Any invalid text raises `ValueError`. A non-`str` argument raises `TypeError`.

## `format_duration(seconds, max_units=None) -> str`
* `seconds` must be an `int` (not `bool`, not `float`), otherwise `TypeError`.
* Output uses units w, d, h, m, s from largest to smallest, omits zero components and joins with a single space: `694861` -> `"1w 1d 1h 1m 1s"`. A day is 24 h, a week 7 days.
* `0` -> `"0s"`. Negative values get a `-` prefix on the whole string: `-90` -> `"-1m 30s"`.
* `max_units` (int >= 1, else `ValueError`) keeps only the first `max_units` NON-ZERO components, truncating (not rounding) the rest: `format_duration(86700, 2)` -> `"1d 5m"`; `format_duration(694861, 2)` -> `"1w 1d"`.
