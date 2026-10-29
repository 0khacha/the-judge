"""Evaluate a node tree."""
import html

from .context import UNDEFINED, lookup
from .errors import TemplateError
from .filters import FILTERS
from .nodes import For, If, Text, Var


def render_var(node, scopes, strict):
    value = lookup(scopes, node.path)
    # A chain that starts with default(...) accepts an undefined variable.
    starts_with_default = bool(node.filters) and node.filters[0][0] == "default"
    if value is UNDEFINED and not starts_with_default:
        if strict:
            raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
        value = ""
    try:
        for name, args in node.filters:
            value = FILTERS[name][0](value, *args)
    except TemplateError as exc:
        raise TemplateError("line %d: %s" % (node.line, exc)) from None
    if value is None:
        return ""
    text = str(value)
    if node.filters and node.filters[-1][0] == "safe":
        return text
    return html.escape(text, quote=True)


def _eval_cond(cond, scopes):
    value = lookup(scopes, cond.path)
    if cond.op is None:
        result = bool(value)
    else:
        equal = value is not UNDEFINED and value == cond.value
        result = equal if cond.op == "==" else not equal
    return not result if cond.negated else result


def _render(nodes, scopes, strict, out):
    for node in nodes:
        if isinstance(node, Text):
            out.append(node.text)
        elif isinstance(node, Var):
            out.append(render_var(node, scopes, strict))
        elif isinstance(node, If):
            for cond, branch in node.branches:
                if _eval_cond(cond, scopes):
                    _render(branch, scopes, strict, out)
                    break
            else:
                if node.else_body is not None:
                    _render(node.else_body, scopes, strict, out)
        elif isinstance(node, For):
            items = lookup(scopes, node.path)
            if items is UNDEFINED:
                if strict:
                    raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
                items = []
            if not isinstance(items, (list, tuple)):
                raise TemplateError("line %d: %r is not a list" % (node.line, node.path))
            length = len(items)
            for index, item in enumerate(items):
                scopes.append({
                    node.var: item,
                    "loop": {
                        "index": index + 1,
                        "index0": index,
                        "first": index == 0,
                        "last": index == length - 1,
                        "length": length,
                    },
                })
                _render(node.body, scopes, strict, out)
                scopes.pop()


def render_nodes(nodes, ctx, strict=False):
    out = []
    _render(nodes, [ctx], strict, out)
    return "".join(out)
