# T6: CSV parser

Create `csvparse.py` with `parse_csv(text)` -> `list[list[str]]` (do not use the `csv` module).

Rules:
- Fields are separated by `,`; records end at `\n` or `\r\n` (the terminator is never part of a field).
- A field starting with `"` is quoted: it runs to the closing `"`; inside, `""` is a literal quote, and commas, `\n` and `\r\n` are kept verbatim as field content.
- After a closing quote the next character must be `,`, a record terminator or end of input, else `ValueError`. An unterminated quote raises `ValueError`.
- A `"` in the middle of an unquoted field is literal. Whitespace is preserved (no stripping).
- A final record terminator does NOT create an extra record: `"a,b\n"` -> `[["a","b"]]`. Empty text -> `[]`.
- A blank line elsewhere is a record with a single empty field: `"a\n\nb"` -> `[["a"],[""],["b"]]`. A trailing comma yields a trailing empty field: `"a,\n"` -> `[["a",""]]`.
