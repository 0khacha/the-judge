# Task: slugify

Create `slug.py` with a function:

    slugify(text: str, max_length: int | None = None) -> str

- Normalise with Unicode NFKD and drop every character that is not ASCII afterwards
  (so "é" becomes "e"; characters with no ASCII decomposition are removed).
- Lower-case.
- Every run of characters that are not ASCII letters or digits becomes a single `-`.
- No leading or trailing `-`. Input with no letters or digits gives `""`.
- If `max_length` is given, the result has at most `max_length` characters. Cut at a `-`
  boundary so no word is split, keeping as many whole words as fit; if even the first
  word is longer than `max_length`, cut that word to `max_length` characters. Never end
  with `-`.
- `max_length < 1` raises ValueError.

Examples (also in `test_visible.py`):

    slugify("Hello World")  == "hello-world"
    slugify("Café au lait") == "cafe-au-lait"
