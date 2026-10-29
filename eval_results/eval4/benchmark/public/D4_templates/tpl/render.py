"""Evaluate a node tree."""
import html

from .context import UNDEFINED, lookup
from .errors import TemplateError
from .filters import FILTERS, SafeStr
from .nodes import For, Text, Var


def render_var(node, scopes, strict):
    value = lookup(scopes, node.path)
    if value is UNDEFINED:
        if strict:
            raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
        value = ""
    for name in node.filters:
        value = FILTERS[name](value)
    if value is None:
        return ""
    if isinstance(value, SafeStr):
        return str(value)
    return html.escape(str(value), quote=True)


def _render(nodes, scopes, strict, out):
    for node in nodes:
        if isinstance(node, Text):
            out.append(node.text)
        elif isinstance(node, Var):
            out.append(render_var(node, scopes, strict))
        elif isinstance(node, For):
            items = lookup(scopes, node.path)
            if items is UNDEFINED:
                if strict:
                    raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
                items = []
            if not isinstance(items, (list, tuple)):
                raise TemplateError("line %d: %r is not a list" % (node.line, node.path))
            for item in items:
                scopes.append({node.var: item})
                _render(node.body, scopes, strict, out)
                scopes.pop()


def render_nodes(nodes, ctx, strict=False):
    out = []
    _render(nodes, [ctx], strict, out)
    return "".join(out)
