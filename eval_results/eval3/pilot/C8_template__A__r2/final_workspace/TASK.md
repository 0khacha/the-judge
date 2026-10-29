# C8: mini template engine

A starter file `tmpl/errors.py` (class `TemplateError(message, line=None)` with a `.line` attribute) is provided; do not change it. Write the rest of the package `tmpl/`: `tmpl/__init__.py` must export `render` and `TemplateError`; put the tokenizer in `tmpl/lexer.py` and the parser/renderer in `tmpl/engine.py` (you may add more modules). Standard library only.

## `render(template, context=None) -> str`
`context` is a dict (default empty). It must not be modified by rendering. All syntax errors are detected before any output is produced, whatever the context is and even inside branches that would not be executed; they raise `TemplateError` with `.line` set as described under "Errors".

### Text and comments
* Anything outside `{{ }}`, `{% %}`, `{# #}` is literal text and is copied unchanged (never escaped). A lone `{` or `}` is just text.
* `{# ... #}` is a comment (may span lines) and produces nothing.

### Variables: `{{ path|filter|filter:"arg" }}`
* Whitespace inside the delimiters is optional (`{{name}}`, `{{  name | upper  }}`).
* `path` is dot-separated. The first segment is an identifier (`[A-Za-z_][A-Za-z0-9_]*`), later segments are `[A-Za-z0-9_]+`. Lookup starts in the context dict. For a dict, a segment is a string key; for a list or tuple, an all-digit segment is an index. Anything else (missing key, index out of range, any other type) makes the value undefined. Undefined never raises; it renders as the empty string.
* Rendering: `None` and undefined render as `""`; everything else uses `str()` (`True` -> `True`, `0` -> `0`).
* Autoescape: the final text is HTML-escaped (`&`->`&amp;`, `<`->`&lt;`, `>`->`&gt;`, `"`->`&quot;`, `'`->`&#x27;`) unless the filter chain contains `safe` anywhere.
* Filters apply left to right: `upper`, `lower` (convert `str(value)`, undefined -> `""`), `length` (len of a str/list/tuple/dict; undefined or other types -> 0), `join:"sep"` (for a list/tuple: `sep.join(str(x) for x in value)`; any other value is left unchanged), `default:"text"` (replaces a value that is undefined, `None` or `""`; other falsy values like `0`, `False`, `[]` are kept), `safe` (no argument). Filter arguments are double-quoted strings in which `\"` is a quote and `\\` a backslash. `default` and `join` require an argument; the other filters take none. Unknown filters and malformed expressions are errors.

### Conditionals
`{% if cond %}...{% elif cond %}...{% else %}...{% endif %}`. `cond` is a path or `not path`; truth is Python truthiness (undefined is false; the string `"0"` is true). Any number of `elif`s, `else` optional and last.

### Loops
`{% for x in path %}...{% else %}...{% endfor %}`. Lists/tuples iterate their items, dicts iterate their keys. If the value is undefined, `None` or empty, the optional `else` block is rendered instead. Inside the body the dict `loop` is available with `loop.index` (1-based), `loop.index0`, `loop.first`, `loop.last`, `loop.length`. The loop variable and `loop` only exist inside the loop: afterwards the previous value (or undefined) is visible again; in nested loops `loop` refers to the innermost one and the outer one is visible again after the inner loop ends.

### Raw blocks
`{% raw %}...{% endraw %}` outputs its content verbatim (no tags or variables are interpreted inside).

### Whitespace control
A `-` right after an opening delimiter (`{{-`, `{%-`, `{#-`) removes ALL whitespace (including newlines) at the end of the literal text immediately before the tag; a `-` right before a closing delimiter (`-}}`, `-%}`, `-#}`) removes all whitespace at the start of the literal text immediately after it. Without markers nothing is trimmed (the newline after a `%}` is kept). In a raw block the markers on `raw` / `endraw` trim the raw content in the same way.

### Errors
Raise `TemplateError` with `.line` = the 1-based line number (counted in the original template) where the relevant tag or delimiter starts, for:
* unknown tag, unknown filter, malformed expression or tag (bad `if`/`for` syntax, `endif`/`else`/`endfor`/`endraw` with extra words, empty `{{ }}`);
* an `endif`, `endfor`, `else`, `elif`, `endraw` in the wrong place (including `elif` or a second `else` after `else`): the line of that tag;
* a block (`if`, `for`, `raw`) that is never closed: the line of the opening tag;
* a `{{`, `{%` or `{#` without its closing delimiter: the line of the opening delimiter.
