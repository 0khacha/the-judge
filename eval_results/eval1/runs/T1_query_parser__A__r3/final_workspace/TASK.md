# Task: query-string parser

Create `querystring.py` with a function:

    parse_query(qs: str) -> dict[str, list[str]]

Parse a URL query string into a dict mapping each key to the list of its values.

- A single leading `?` is ignored.
- Pairs are separated by `&`; empty segments (e.g. from `&&`) are ignored.
- Each pair is split on the FIRST `=`. A segment without `=` is a key with value `""`.
- In keys and values, `+` means a space, and `%XX` percent-escapes are decoded as UTF-8.
  An invalid escape (such as `%zz` or a trailing `%4`) is kept literally.
- Repeated keys collect their values in order. Keys appear in first-seen order.

Examples (also in `test_visible.py`):

    parse_query("a=1&b=2")         == {"a": ["1"], "b": ["2"]}
    parse_query("a=1&a=2")         == {"a": ["1", "2"]}
    parse_query("name=John+Smith") == {"name": ["John Smith"]}
