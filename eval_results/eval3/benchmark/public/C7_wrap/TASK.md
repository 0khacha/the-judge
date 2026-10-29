# C7: Unicode-aware text wrapper

Write `wrap.py` (project root, standard library only; do not use the `textwrap` module) with:

## `display_width(s) -> int`
Number of terminal columns a string occupies: each character counts 1, except
* characters whose `unicodedata.east_asian_width` is `"W"` or `"F"` count 2;
* characters whose `unicodedata.category` is `"Mn"` or `"Me"` (combining marks) count 0.

## `wrap_text(text, width, indent="", subsequent_indent="") -> str`
Wraps text so that every output line has display width <= `width`.

* Line endings: `\r\n` and lone `\r` are treated as `\n`.
* Paragraphs: a blank line (empty or only spaces/tabs) separates paragraphs. Any number of blank lines is one separator. Output paragraphs are joined by exactly one blank line (`"\n\n"`). Leading/trailing blank lines are dropped. Text with no words (including `""`) gives `""`.
* Inside a paragraph the "whitespace" characters are ONLY space, tab and newline. Runs of them collapse to a single break opportunity and are rendered as one space; leading/trailing whitespace of a paragraph is dropped. Other characters, including the no-break space U+00A0 and the ideographic space U+3000, are ordinary word characters and are kept unchanged (so `str.split()` is not suitable).
* Greedy filling: words are added to the current line, separated by one space, as long as the line's display width stays <= the available width. Lines never end with spaces.
* Indentation: the first line of every paragraph is prefixed with `indent`, all other lines of the paragraph with `subsequent_indent`. Indent counts toward the width: available width = `width - display_width(prefix)`.
* If `width - display_width(indent) < 2` or `width - display_width(subsequent_indent) < 2` raise `ValueError` (at least 2 columns must remain for text).
* Hyphen breaks: a word may also be broken right after a `-` when the characters immediately before and after that hyphen are both alphanumeric (`str.isalnum()`). The hyphen stays at the end of the first part and the next part continues the line with no space between. So `well-known` can wrap as `well-` / `known`, but `a--b`, `-x` and `x-` have no break points.
* Long chunks: a chunk (a word, or a part of a word after splitting at hyphens) whose display width exceeds the available width is hard-broken. It first starts on a fresh line (unless the current line is empty), then is split character by character so each piece fits the available width; the last piece stays as the current line so later words may follow it on the same line. A character is never split across lines, a 2-column character that does not fit moves to the next line, and a zero-width character always stays on the line of the preceding character (even if that makes the line exactly full).
* The `indent` is used for the first output line of each paragraph, whichever kind of break produced the lines.
