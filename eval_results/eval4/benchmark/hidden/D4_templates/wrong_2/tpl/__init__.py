"""Minimal text template engine."""
from .errors import TemplateError
from .parser import parse
from .render import render_nodes


def render(source, ctx=None, strict=False):
    nodes = parse(source)
    return render_nodes(nodes, ctx or {}, strict)


__all__ = ["render", "TemplateError"]
