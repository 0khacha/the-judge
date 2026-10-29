# C3: strict CSV parser

Write `csvparse.py` (project root, standard library only; do NOT use the `csv` module) with:

## `class CsvError(ValueError)`
Has an attribute `line` (int or `None`): the 1-based line number the problem is reported at (see below).

## `parse_csv(text, delimiter=",") -> list[list[str]]`
Parses a whole CSV document held in `text` into a list of records, each a list of strings.

* `delimiter` must be a single character that is not `"`, `\r` or `\n`; otherwise `ValueError` (plain, not `CsvError`).
* A leading BOM (U+FEFF) is removed.
* Record separators are `\n`, `\r\n` or `\r` (they may be mixed in one document). A final separator at the end of the text does not create an extra record. Empty text gives `[]`.
* A completely empty line (nothing between two separators, outside quotes) is skipped and produces no record. A line containing only spaces is NOT empty: it is a record with one field of spaces. A line that is just `""` is a record with one empty field.
* An empty field is the empty string, including a trailing one: `a,b,` -> `["a","b",""]`.
* Whitespace is never stripped; fields keep leading/trailing spaces.
* A field that starts with `"` is quoted. Inside it the delimiter and line breaks are literal text, and `""` stands for one `"`. Line breaks inside quotes are kept exactly as written (`\r\n` stays `\r\n`).
* A `"` in the middle of an unquoted field is an ordinary character (`ab"c` is the field `ab"c`).
* After the closing quote of a quoted field only a delimiter, a record separator or the end of the text may follow; anything else raises `CsvError` whose `line` is the line number where the offending character is.
* A quoted field that is never closed raises `CsvError` whose `line` is the line where that quoted field STARTED. (`"abc""` is unterminated: the last two quotes are an escaped quote.)
* Line numbers start at 1 and increase by one for every `\n`, `\r\n` or lone `\r` in the text, including those inside quoted fields and skipped empty lines (a BOM does not count as anything).

## `parse_csv_dicts(text, delimiter=",") -> list[dict]`
Uses the first record as the header. Header names are stripped of surrounding whitespace. Returns one dict per remaining record (keys in header order). Rules:
* No records at all, or only a header, gives `[]`.
* An empty header name (after stripping) or a duplicate header name raises `CsvError`.
* A data record shorter than the header is padded with `""`; a longer one raises `CsvError`.
* Errors from `parse_csv` propagate unchanged.
