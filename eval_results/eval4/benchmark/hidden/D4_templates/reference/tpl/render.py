"""Evaluate a node tree."""
import html

from .context import UNDEFINED, lookup
from .errors import TemplateError
from .filters import FILTERS, SafeStr
from .nodes import For, If, Text, Var


def render_var(node, scopes, strict):
    value = lookup(scopes, node.path)
    has_default = bool(node.filters) and node.filters[0][0] == "default"
    if value is UNDEFINED and not has_default:
        if strict:
            raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
        value = ""
    for name, args in node.filters:
        try:
            value = FILTERS[name](value, *args)
        except TemplateError as exc:
            raise TemplateError("line %d: %s" % (node.line, exc))
    if value is None or value is UNDEFINED:
        return ""
    if isinstance(value, SafeStr):
        return str(value)
    return html.escape(str(value), quote=True)


def cond_true(cond, scopes):
    value = lookup(scopes, cond.path)
    defined = value is not UNDEFINED
    if cond.op is None:
        result = bool(value)
    elif cond.op == "==":
        result = defined and value == cond.literal
    else:
        result = not (defined and value == cond.literal)
    return (not result) if cond.negate else result


def _render(nodes, scopes, strict, out):
    for node in nodes:
        if isinstance(node, Text):
            out.append(node.text)
        elif isinstance(node, Var):
            out.append(render_var(node, scopes, strict))
        elif isinstance(node, If):
            for cond, body in node.branches:
                if cond is None or cond_true(cond, scopes):
                    _render(body, scopes, strict, out)
                    break
        elif isinstance(node, For):
            items = lookup(scopes, node.path)
            if items is UNDEFINED:
                if strict:
                    raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
                items = []
            if not isinstance(items, (list, tuple)):
                raise TemplateError("line %d: %r is not a list" % (node.line, node.path))
            total = len(items)
            for i, item in enumerate(items):
                loop = {"index": i + 1, "index0": i, "first": i == 0, "last": i == total - 1,
                        "length": total}
                scopes.append({"loop": loop, node.var: item})
                _render(node.body, scopes, strict, out)
                scopes.pop()


def render_nodes(nodes, ctx, strict=False):
    out = []
    _render(nodes, [ctx], strict, out)
    return "".join(out)
