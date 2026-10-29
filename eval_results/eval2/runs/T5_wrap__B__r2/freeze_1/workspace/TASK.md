# T5: display-width text wrapping

Create `wrap.py` with:

- `display_width(s)` -> int: terminal columns used by `s`. Per character: width 0 if `unicodedata.combining(ch) != 0` or its category is `Mn`, `Me` or `Cf`; width 2 if `unicodedata.east_asian_width(ch)` is `"W"` or `"F"`; otherwise 1.
- `wrap_text(text, width)` -> list[str] of lines, each (when possible) at most `width` columns:
  1. Words are `text.split()` (any whitespace run separates words; whitespace is collapsed to single spaces). Empty/blank text -> `[]`.
  2. Greedy fill: put as many words per line as fit, separated by one space (the space counts as 1 column).
  3. A word wider than `width` is hard-split into pieces character by character: complete pieces each become their own line, and the final piece starts a new current line which following words may join. A zero-width character never starts a new piece (it stays attached to the preceding character). A single character wider than `width` is placed alone on its line (never dropped).
  4. `width < 1` (or non-int) raises `ValueError`.
