# tpl - a minimal text template engine

```python
from tpl import render
render("Hello {{ user.name | upper }}!", {"user": {"name": "ann"}})   # 'Hello ANN!'
```

Syntax

* `{{ path }}` - value of a (dotted) variable: dict keys, then attributes, then list indexes (`items.0`). `None` and undefined variables print as empty text.
* `{{ path | f1 | f2 }}` - filters, applied left to right. Built in: `upper`, `lower`, `title`, `trim`, `length`, `safe`. Unknown filters are a `TemplateError`.
* `{% for x in path %} ... {% endfor %}` - loop over a list (undefined = empty loop). Loop variable is visible only inside the loop.
* `{# comment #}` - dropped.
* Output is HTML-escaped (`& < > " '`) unless the value was produced by `safe` as the last filter of the chain. Filters that run after `safe` return plain text again.
* `render(source, ctx, strict=False)`: with `strict=True` an undefined variable in `{{ }}` or in a `for` source raises `TemplateError`.
* All errors are `TemplateError`; messages start with `line N:` (the line of the offending tag).

Modules: `tpl.lexer` (tokens), `tpl.parser` (syntax tree), `tpl.nodes`, `tpl.filters`, `tpl.context` (variable lookup), `tpl.render` (evaluation), `tpl.cli` (`python -m tpl.cli template.txt data.json`).
