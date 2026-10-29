import copy

import pytest
from tmpl import render, TemplateError


def test_package_exports():
    import tmpl.errors
    assert tmpl.errors.TemplateError is TemplateError
    assert issubclass(TemplateError, Exception)


def test_none_context_and_plain_text():
    assert render("hi") == "hi"
    assert render("{{ a }}") == ""
    assert render("{{ a }}", None) == ""


@pytest.mark.parametrize("tpl", ["Hi {{ name }}!", "Hi {{name}}!", "Hi {{    name   }}!", "Hi {{\tname\n}}!"])
def test_variable_whitespace(tpl):
    assert render(tpl, {"name": "Bob"}) == "Hi Bob!"


def test_lone_braces_are_text():
    assert render("a { b } c {x} {{ y }}", {"y": 1}) == "a { b } c {x} 1"
    assert render("a }} b") == "a }} b"
    assert render("{ {{ y }} }", {"y": 1}) == "{ 1 }"


@pytest.mark.parametrize("tpl,exp", [
    ("{{ user.name }}", "Ann"), ("{{ user.tags.1 }}", "b"), ("{{ user.tags.0 }}", "a"),
    ("{{ user.tags.5 }}", ""), ("{{ user.nope.x }}", ""), ("{{ user.name.first }}", ""),
    ("{{ pair.1 }}", "y"), ("{{ pair.2 }}", ""), ("{{ nope }}", ""), ("{{ user.tags.x }}", ""),
])
def test_paths(tpl, exp):
    ctx = {"user": {"name": "Ann", "tags": ["a", "b"]}, "pair": ("x", "y")}
    assert render(tpl, ctx) == exp


@pytest.mark.parametrize("value,exp", [(None, ""), (True, "True"), (False, "False"), (0, "0"), (1.5, "1.5"), ("s", "s")])
def test_value_rendering(value, exp):
    assert render("{{ v }}", {"v": value}) == exp


def test_autoescape():
    assert render("{{ x }}", {"x": "<a href=\"u\">&'"}) == "&lt;a href=&quot;u&quot;&gt;&amp;&#x27;"
    assert render("<b>{{ x }}</b>", {"x": "<"}) == "<b>&lt;</b>"
    assert render("{{ x }}", {"x": "&amp;"}) == "&amp;amp;"


def test_safe():
    assert render("{{ x|safe }}", {"x": "<b>"}) == "<b>"
    assert render("{{ x|safe|upper }}", {"x": "<b>"}) == "<B>"
    assert render("{{ x|upper|safe }}", {"x": "<b>"}) == "<B>"
    assert render("{{ x|upper }}", {"x": "<b>"}) == "&lt;B&gt;"


@pytest.mark.parametrize("tpl,exp", [
    ("{{ name|upper }}", "BOB"), ("{{ name|lower }}", "bob"), ("{{ name|upper|lower }}", "bob"),
    ("{{ name | upper }}", "BOB"), ("{{ missing|upper }}", ""),
    ("{{ xs|length }}", "3"), ("{{ name|length }}", "3"), ("{{ d|length }}", "2"),
    ("{{ missing|length }}", "0"), ("{{ n|length }}", "0"), ("{{ t|length }}", "2"),
])
def test_basic_filters(tpl, exp):
    ctx = {"name": "Bob", "xs": [1, 2, 3], "d": {"a": 1, "b": 2}, "n": 5, "t": (1, 2)}
    assert render(tpl, ctx) == exp


def test_join():
    ctx = {"xs": ["a", "b", "c"], "ns": [1, 2], "name": "Bob"}
    assert render('{{ xs|join:", " }}', ctx) == "a, b, c"
    assert render('{{ ns|join:"+" }}', ctx) == "1+2"
    assert render('{{ xs|join:"<br>" }}', ctx) == "a&lt;br&gt;b&lt;br&gt;c"
    assert render('{{ xs|join:"<br>"|safe }}', ctx) == "a<br>b<br>c"
    assert render('{{ name|join:"-" }}', ctx) == "Bob"
    assert render('{{ xs|join:"" }}', ctx) == "abc"


def test_default():
    assert render('{{ m|default:"n/a" }}', {}) == "n/a"
    assert render('{{ m|default:"n/a" }}', {"m": None}) == "n/a"
    assert render('{{ m|default:"n/a" }}', {"m": ""}) == "n/a"
    assert render('{{ m|default:"n/a" }}', {"m": 0}) == "0"
    assert render('{{ m|default:"n/a" }}', {"m": False}) == "False"
    assert render('{{ m|default:"n/a" }}', {"m": "x"}) == "x"
    assert render('{{ m|default:"<x>" }}', {}) == "&lt;x&gt;"
    assert render('{{ m|default:"x"|upper }}', {}) == "X"
    assert render('{{ m|default:"a|b" }}', {}) == "a|b"
    assert render('{{ m|default:"" }}', {}) == ""


def test_filter_arg_escapes():
    assert render('{{ m|default:"say \\"hi\\"" }}', {}) == "say &quot;hi&quot;"
    assert render('{{ m|default:"a\\\\b" }}', {}) == "a\\b"


@pytest.mark.parametrize("value,truthy", [
    (0, False), ("", False), ([], False), ({}, False), (None, False), (False, False),
    ("0", True), ([0], True), (1, True), ("x", True), (-1, True),
])
def test_truthiness(value, truthy):
    assert render("{% if v %}T{% else %}F{% endif %}", {"v": value}) == ("T" if truthy else "F")
    assert render("{% if not v %}T{% else %}F{% endif %}", {"v": value}) == ("F" if truthy else "T")


def test_if_missing_and_dotted():
    assert render("{% if v %}T{% else %}F{% endif %}", {}) == "F"
    assert render("{% if not v %}T{% endif %}", {}) == "T"
    assert render("{% if user.admin %}T{% else %}F{% endif %}", {"user": {"admin": True}}) == "T"
    assert render("{% if user.admin %}T{% else %}F{% endif %}", {"user": {}}) == "F"
    assert render("{%if v%}T{%endif%}", {"v": 1}) == "T"


@pytest.mark.parametrize("ctx,exp", [
    ({"a": 1, "b": 1}, "A"), ({"b": 1, "c": 1}, "B"), ({"c": 1}, "C"), ({}, "D"),
])
def test_elif_chain(ctx, exp):
    assert render("{% if a %}A{% elif b %}B{% elif c %}C{% else %}D{% endif %}", ctx) == exp


def test_elif_without_else_and_nested():
    assert render("{% if a %}A{% elif b %}B{% endif %}", {}) == ""
    tpl = "{% if a %}[{% if b %}x{% else %}y{% endif %}]{% else %}n{% endif %}"
    assert render(tpl, {"a": 1, "b": 1}) == "[x]"
    assert render(tpl, {"a": 1}) == "[y]"
    assert render(tpl, {}) == "n"
    assert render("{% if a %}A{% elif not b %}B{% endif %}", {}) == "B"


def test_for_basic():
    assert render("{% for x in xs %}[{{ x }}]{% endfor %}", {"xs": [1, 2]}) == "[1][2]"
    assert render("{% for x in xs %}[{{ x }}]{% endfor %}", {"xs": (3, 4)}) == "[3][4]"
    assert render("{% for k in d %}{{ k }}{% endfor %}", {"d": {"b": 1, "a": 2}}) == "ba"
    assert render("{% for u in users %}{{ u.name }},{% endfor %}", {"users": [{"name": "a"}, {"name": "b"}]}) == "a,b,"
    assert render("{% for x in a.b %}{{ x }}{% endfor %}", {"a": {"b": [1, 2]}}) == "12"
    assert render("{%for x in xs%}{{x}}{%endfor%}", {"xs": [1]}) == "1"


def test_loop_variables():
    tpl = "{% for x in xs %}{{ loop.index }}/{{ loop.index0 }}/{{ loop.length }}/{{ loop.first }}/{{ loop.last }};{% endfor %}"
    assert render(tpl, {"xs": [7, 8]}) == "1/0/2/True/False;2/1/2/False/True;"
    assert render(tpl, {"xs": [7]}) == "1/0/1/True/True;"


def test_loop_conditions():
    tpl = ("{% for x in xs %}{% if loop.first %}[{% endif %}{{ x }}"
           "{% if not loop.last %},{% endif %}{% if loop.last %}]{% endif %}{% endfor %}")
    assert render(tpl, {"xs": [1, 2, 3]}) == "[1,2,3]"


@pytest.mark.parametrize("ctx,exp", [
    ({"xs": []}, "none"), ({}, "none"), ({"xs": None}, "none"), ({"xs": {}}, "none"),
    ({"xs": [0]}, "a"), ({"xs": [None, None]}, "aa"),
])
def test_for_else(ctx, exp):
    assert render("{% for x in xs %}a{% else %}none{% endfor %}", ctx) == exp


def test_for_without_else_empty():
    assert render("[{% for x in xs %}a{% endfor %}]", {"xs": []}) == "[]"


def test_nested_loops_restore_outer():
    tpl = ("{% for a in xs %}{{ loop.index }}:{% for b in ys %}{{ loop.index }}{% endfor %}"
           "{{ loop.index }};{% endfor %}")
    assert render(tpl, {"xs": [1, 2], "ys": [1, 1]}) == "1:121;2:122;"


def test_loop_scope():
    assert render("{{ x }}{% for x in xs %}{{ x }}{% endfor %}{{ x }}", {"x": "o", "xs": [1, 2]}) == "o12o"
    assert render("{% for x in xs %}{{ x }}{% endfor %}[{{ x }}]", {"xs": [1]}) == "1[]"
    assert render("{% for x in xs %}{% endfor %}[{{ loop.index }}]", {"xs": [1]}) == "[]"


def test_context_not_modified():
    ctx = {"xs": [1, 2], "x": "o", "d": {"k": [1]}}
    snap = copy.deepcopy(ctx)
    render("{% for x in xs %}{{ x }}{% for y in d.k %}{{ y }}{% endfor %}{% endfor %}", ctx)
    assert ctx == snap


def test_comments():
    assert render("a{# hi\nthere #}b") == "ab"
    assert render("a{# {{ x }} {% if %} #}b", {"x": 1}) == "ab"


def test_raw():
    assert render("{% raw %}{{ x }} {% if %}{% endraw %}", {"x": 1}) == "{{ x }} {% if %}"
    assert render("{% raw %}  a  {% endraw %}") == "  a  "
    assert render("{% raw %}{{x}}{% endraw %}{{ x }}", {"x": 1}) == "{{x}}1"
    assert render("{% raw %}{# c #}{% endif %}{% endraw %}") == "{# c #}{% endif %}"
    assert render("{% raw %}a{% endraw %}-{% raw %}b{% endraw %}") == "a-b"
    assert render("{% raw %}{% endraw %}x") == "x"


def test_raw_whitespace_control():
    assert render("a {%- raw -%} {{x}} {%- endraw -%} b") == "a{{x}}b"


@pytest.mark.parametrize("tpl,ctx,exp", [
    ("a  {%- if x -%}  b  {%- endif -%}  c", {"x": 1}, "abc"),
    ("a  {%- if x -%}  b  {%- endif -%}  c", {"x": 0}, "ac"),
    ("x\n\n  {{- y -}}\n\n z", {"y": "Y"}, "xYz"),
    ("a {#- c -#} b", {}, "ab"),
    ("a  {{- y }}  b", {"y": "Y"}, "aY  b"),
    ("a  {{ y -}}  b", {"y": "Y"}, "a  Yb"),
    ("a\n{% if x %}\nb\n{% endif %}\nc", {"x": 1}, "a\n\nb\n\nc"),
    ("line1\n{%- if x %}\nline2{% endif %}", {"x": 1}, "line1\nline2"),
    ("{{ a }}{{- b }}", {"a": "A", "b": "B"}, "AB"),
    ("{% for x in xs -%}\n  {{ x }}\n{%- endfor %}", {"xs": [1, 2]}, "12"),
])
def test_whitespace_control(tpl, ctx, exp):
    assert render(tpl, ctx) == exp


@pytest.mark.parametrize("tpl,line", [
    ("a\nb\n{% frobnicate %}", 3),
    ("{% frob %}", 1),
    ("{% if x %}\n\nhello", 1),
    ("a\n{% for x in xs %}b", 2),
    ("{% if a %}{% else %}x", 1),
    ("{% for x in xs %}a\n{% else %}\nb", 1),
    ("{% for x in xs %}\n{% if a %}\n{% endfor %}\n", 3),
    ("{% if a %}\n{% for x in y %}\n{% endif %}\n{% endfor %}", 3),
    ("ok\n{% endif %}", 2),
    ("{% endfor %}", 1),
    ("\n\n{% endraw %}", 3),
    ("{% for x in xs %}\n{% endif %}", 2),
    ("x\n\n{{ name", 3),
    ("{# never closed", 1),
    ("a\n{% if x", 2),
    ("{% else %}", 1),
    ("{% if a %}\n{% else %}\nx\n{% else %}\n{% endif %}", 4),
    ("{% if a %}{% else %}\n{% elif b %}{% endif %}", 2),
    ("{% for x in xs %}a\n{% else %}\nb\n{% else %}\nc{% endfor %}", 4),
    ("{% raw %}\nabc", 1),
    ("a\n{{ x|bogus }}", 2),
    ("{{ x|default }}", 1),
    ('{{ x|upper:"a" }}', 1),
    ("{{ }}", 1),
    ("\n{{ 1x }}", 2),
    ("{{ a..b }}", 1),
    ("{{ x| }}", 1),
    ("{{ x y }}", 1),
    ("{% for in xs %}{% endfor %}", 1),
    ("{% for x xs %}{% endfor %}", 1),
    ("{% if %}{% endif %}", 1),
    ("{% if a b %}{% endif %}", 1),
    ("{% if a %}{% endif x %}", 1),
    ("{# a\nb\nc #}{% bogus %}", 3),
    ("{% raw %}a\nb{% endraw %}\n{% bogus %}", 3),
    ("a\n\n  {%- bogus %}", 3),
    ("{% if a %}\n{% elif %}{% endif %}", 2),
])
def test_errors_have_line_numbers(tpl, line):
    with pytest.raises(TemplateError) as ei:
        render(tpl, {"a": 1, "xs": [1]})
    assert ei.value.line == line


def test_errors_detected_in_unexecuted_branches():
    with pytest.raises(TemplateError) as ei:
        render("{% if x %}\n{{ y|bogus }}{% endif %}", {"x": False})
    assert ei.value.line == 2
    with pytest.raises(TemplateError):
        render("{% for i in xs %}{% frob %}{% endfor %}", {"xs": []})
