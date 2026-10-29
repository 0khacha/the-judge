"""Evaluate a node tree."""
import html

from .context import UNDEFINED, lookup
from .errors import TemplateError
from .filters import FILTERS, SafeStr
from .nodes import For, If, Text, Var


def render_var(node, scopes, strict):
    value = lookup(scopes, node.path)
    starts_with_default = bool(node.filters) and node.filters[0].name == "default"
    if value is UNDEFINED and not starts_with_default:
        if strict:
            raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))
        value = ""
    try:
        for f in node.filters:
            value = FILTERS[f.name](value, *f.args)
    except TemplateError as exc:
        raise TemplateError("line %d: %s" % (node.line, exc)) from None
    if value is None:
        return ""
    if isinstance(value, SafeStr):
        return str(value)
    return html.escape(str(value), quote=True)


def eval_cond(cond, scopes):
    value = lookup(scopes, cond.path)
    if cond.op is None:
        result = bool(value)
    else:
        equal = value is not UNDEFINED and value == cond.literal
        result = equal if cond.op == "==" else not equal
    return not result if cond.negated else result


def _render(nodes, scopes, strict, out):
    for node in nodes:
        if isinstance(node, Text):
            out.append(node.text)
        elif isinstance(node, Var):
            out.append(render_var(node, scopes, strict))
        elif isinstance(node, If):
            for branch in node.branches:
                if eval_cond(branch.cond, scopes):
                    _render(branch.body, scopes, strict, out)
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
            n = len(items)
            for i, item in enumerate(items):
                frame = {"loop": {"index": i + 1, "index0": i, "first": i == 0,
                                  "last": i == n - 1, "length": n}}
                frame[node.var] = item
                scopes.append(frame)
                _render(node.body, scopes, strict, out)
                scopes.pop()


def render_nodes(nodes, ctx, strict=False):
    out = []
    _render(nodes, [ctx], strict, out)
    return "".join(out)
