# Ticket: conditionals, filter arguments and a loop variable

Templates need a bit more logic.

1. **Filter arguments.** A filter may be written with arguments: `{{ x | join(", ") }}`. Arguments are separated by commas and are either string literals (single or double quoted; the text between the quotes is taken literally and may contain `|`, `,`, `(` or `)`) or integers (optional leading `-`). Filters can be chained with and without arguments. Giving a filter the wrong number of arguments, or a malformed argument, is a `TemplateError` (raised when the template is parsed) with a `line N:` message. Filters without arguments, `{{ x | upper }}`, keep working.
2. **New filters.**
   * `default(fallback)`: result is `fallback` if the variable is undefined or `None`; any other value (including `""` and `0`) is kept. It is meant to be the first filter of a chain.
   * `join(sep)`: joins a list or tuple, converting every item with `str`; any other value raises `TemplateError` (message starting with `line N:`).
   * `truncate(n)`: `str(value)` unchanged if it has at most `n` characters, otherwise the first `n` characters followed by `...`. A negative `n` raises `TemplateError` with a `line N:` message.
3. **strict mode and `default`.** With `strict=True`, an undefined variable normally raises `TemplateError`; it does not when the first filter of its chain is `default(...)`.
4. **Escaping** is unchanged and applies to the new filters too: the result is HTML-escaped unless the last filter that ran was `safe`. So `{{ x | default("<none>") }}` prints `&lt;none&gt;`, `{{ x | default("<b>") | safe }}` prints `<b>`, and `join`/`truncate` results are escaped.
5. **Conditionals.** `{% if COND %}...{% elif COND %}...{% else %}...{% endif %}` (`elif` and `else` optional, any number of `elif`). `COND` is one of: `path`, `not path`, `path == LITERAL`, `path != LITERAL`, `not path == LITERAL` (this negates the comparison); `LITERAL` is a quoted string or an integer. A plain `path` is true when the value is truthy (Python rules). An undefined variable is falsy and never equal to a literal, also in strict mode (no error). `if` blocks may be nested and may contain, or be inside, `for` blocks. Tags do not swallow surrounding whitespace.
6. **Block errors**, all `TemplateError` with a `line N:` message: a bad condition (line of the tag); `elif`/`else`/`endif` without an open `if`, `elif` or a second `else` after `else` (line of that tag); `endif` closing an open `for` or `endfor` closing an open `if` (line of the closing tag); an `if` or `for` never closed (line where it was opened; if several are open, the innermost one).
7. **Loop variable.** Inside a `for`, `loop` is available with `loop.index` (starts at 1), `loop.index0`, `loop.first` and `loop.last` (booleans) and `loop.length`. In nested loops `loop` refers to the innermost loop, and after the inner loop ends it refers to the outer loop again. Outside any loop `loop` is undefined (unless the context defines it).

Existing behaviour (variable lookup, `for`, comments, escaping, strict mode, the CLI) must keep working.
