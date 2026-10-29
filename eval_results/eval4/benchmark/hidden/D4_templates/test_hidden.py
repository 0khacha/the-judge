import json

import pytest

from tpl import TemplateError, render
from tpl.cli import main


def err(src, ctx=None, strict=False):
    with pytest.raises(TemplateError) as e:
        render(src, ctx or {}, strict=strict)
    return str(e.value)


# ------------------------------------------------------------------ new: filters
def test_new_join_basic_and_quotes():
    assert render('{{ xs | join(", ") }}', {"xs": ["a", "b", "c"]}) == "a, b, c"
    assert render("{{ xs | join('-') }}", {"xs": [1, 2]}) == "1-2"
    assert render('{{ xs | join("") }}', {"xs": ("x", "y")}) == "xy"


def test_new_join_separator_with_pipe_and_parens():
    assert render('{{ xs | join(" | ") }}', {"xs": ["a", "b"]}) == "a | b"
    assert render('{{ xs | join(", (") }}', {"xs": ["a", "b"]}) == "a, (b"
    assert render('{{ xs | join(")") | upper }}', {"xs": ["a", "b"]}) == "A)B"


def test_new_join_escapes_result():
    assert render('{{ xs | join("<") }}', {"xs": ["a", "b"]}) == "a&lt;b"


def test_new_join_needs_list():
    assert "line 2:" in err('x\n{{ s | join(",") }}', {"s": "abc"})


def test_new_default_basic():
    assert render('{{ x | default("n/a") }}', {}) == "n/a"
    assert render('{{ x | default("n/a") }}', {"x": None}) == "n/a"
    assert render('{{ x | default("n/a") }}', {"x": "v"}) == "v"


def test_new_default_keeps_empty_and_zero():
    assert render('[{{ x | default("n/a") }}]', {"x": ""}) == "[]"
    assert render('[{{ x | default("n/a") }}]', {"x": 0}) == "[0]"


def test_new_default_integer_and_dotted():
    assert render("{{ x | default(-5) }}", {}) == "-5"
    assert render('{{ a.b.c | default("z") }}', {"a": {}}) == "z"
    assert render('{{ a.b | default("z") }}', {"a": {"b": "q"}}) == "q"


def test_new_default_then_other_filters():
    assert render('{{ x | default("anon") | upper }}', {}) == "ANON"
    assert render('{{ x | default("anon") | upper }}', {"x": "bo"}) == "BO"


def test_new_default_is_escaped_unless_safe():
    assert render('{{ x | default("<none>") }}', {}) == "&lt;none&gt;"
    assert render('{{ x | default("<b>") | safe }}', {}) == "<b>"


def test_new_strict_default_does_not_raise():
    assert render('{{ x | default("d") }}', {}, strict=True) == "d"
    assert "undefined" in err("{{ x | upper }}", {}, strict=True)
    assert "line 1:" in err('{{ x | upper | default("d") }}', {}, strict=True)


def test_new_truncate():
    assert render("{{ s | truncate(5) }}", {"s": "hello world"}) == "hello..."
    assert render("{{ s | truncate(5) }}", {"s": "hello"}) == "hello"
    assert render("{{ s | truncate(0) }}", {"s": "x"}) == "..."
    assert render("{{ s | truncate(3) }}", {"s": 12345}) == "123..."


def test_new_truncate_negative_and_escaping():
    assert "line 1:" in err("{{ s | truncate(-1) }}", {"s": "x"})
    assert render("{{ s | truncate(3) }}", {"s": "<b>xyz"}) == "&lt;b&gt;..."


def test_new_safe_only_effective_last():
    assert render("{{ s | safe | truncate(3) }}", {"s": "<b>xyz"}) == "&lt;b&gt;..."
    assert render("{{ s | truncate(3) | safe }}", {"s": "<b>xyz"}) == "<b>..."


def test_new_filter_arity_and_literal_errors():
    assert "line 1:" in err("{{ x | join }}")
    assert "line 1:" in err("{{ x | upper(1) }}")
    assert "line 3:" in err('a\nb\n{{ x | join(",", "b") }}')
    assert "line 1:" in err("{{ x | join(a) }}")
    assert "line 1:" in err('{{ x | join("a) }}')
    assert "line 1:" in err("{{ x | truncate() }}")


def test_new_arg_errors_raised_even_if_branch_not_taken():
    assert "line 2:" in err("{% if no %}\n{{ x | join }}{% endif %}")


# ------------------------------------------------------------------ new: if
def test_new_if_else():
    t = "{% if x %}yes{% else %}no{% endif %}"
    assert render(t, {"x": 1}) == "yes"
    assert render(t, {"x": 0}) == "no"
    assert render("a{% if x %}b{% endif %}c", {"x": 0}) == "ac"


def test_new_elif_chain():
    t = "{% if a == 1 %}one{% elif a == 2 %}two{% elif a == 3 %}three{% else %}many{% endif %}"
    assert [render(t, {"a": i}) for i in (1, 2, 3, 4)] == ["one", "two", "three", "many"]


def test_new_first_matching_branch_only():
    assert render("{% if x %}A{% elif x %}B{% else %}C{% endif %}", {"x": 1}) == "A"


def test_new_not_and_comparisons():
    ctx = {"s": "ab", "n": 3}
    assert render("{% if not s %}Y{% else %}N{% endif %}", ctx) == "N"
    assert render('{% if s == "ab" %}Y{% endif %}', ctx) == "Y"
    assert render("{% if s == 'ab' %}Y{% endif %}", ctx) == "Y"
    assert render('{% if s != "ab" %}Y{% else %}N{% endif %}', ctx) == "N"
    assert render("{% if n == 3 %}Y{% endif %}", ctx) == "Y"
    assert render("{% if n != 3 %}Y{% else %}N{% endif %}", ctx) == "N"
    assert render('{% if n == "3" %}Y{% else %}N{% endif %}', ctx) == "N"
    assert render("{% if n == -3 %}Y{% else %}N{% endif %}", {"n": -3}) == "Y"


def test_new_not_negates_comparison():
    assert render('{% if not s == "ab" %}Y{% else %}N{% endif %}', {"s": "ab"}) == "N"
    assert render('{% if not s == "ab" %}Y{% else %}N{% endif %}', {"s": "x"}) == "Y"


def test_new_truthiness():
    t = "{% if v %}T{% else %}F{% endif %}"
    assert [render(t, {"v": v}) for v in (0, "", [], None, "0", [0], 5)] == list("FFFFTTT")


def test_new_undefined_in_if_never_errors_in_strict():
    t = '{% if nope %}A{% elif nope == "x" %}B{% elif nope != "x" %}C{% endif %}'
    assert render(t, {}, strict=True) == "C"
    assert render("{% if a.b.c %}A{% else %}B{% endif %}", {"a": {}}, strict=True) == "B"
    assert render("{% if not nope %}A{% endif %}", {}, strict=True) == "A"


def test_new_strict_still_applies_inside_taken_branch():
    assert "undefined" in err("{% if ok %}{{ nope }}{% endif %}", {"ok": 1}, strict=True)
    assert render("{% if ok %}{% else %}{{ nope }}{% endif %}", {"ok": 1}, strict=True) == ""


def test_new_nested_if_and_whitespace():
    t = "{% if a %}\n  {% if b %}AB{% else %}A{% endif %}\n{% endif %}"
    assert render(t, {"a": 1, "b": 1}) == "\n  AB\n"
    assert render(t, {"a": 1, "b": 0}) == "\n  A\n"
    assert render(t, {"a": 0, "b": 1}) == ""


def test_new_if_with_for_both_ways():
    t = "{% for x in xs %}{% if x == 2 %}[{{ x }}]{% else %}{{ x }}{% endif %}{% endfor %}"
    assert render(t, {"xs": [1, 2, 3]}) == "1[2]3"
    t2 = "{% if xs %}{% for x in xs %}{{ x }}{% endfor %}{% else %}none{% endif %}"
    assert render(t2, {"xs": [1, 2]}) == "12"
    assert render(t2, {"xs": []}) == "none"


def test_new_block_errors_have_lines():
    assert "line 2:" in err("a\n{% if %}x{% endif %}")
    assert "line 2:" in err("a\n{% if a b %}x{% endif %}")
    assert "line 3:" in err("a\nb\n{% elif x %}")
    assert "line 1:" in err("{% else %}")
    assert "line 2:" in err("a\n{% endif %}")
    assert "line 3:" in err("{% if x %}\n{% else %}\n{% else %}{% endif %}")
    assert "line 3:" in err("{% if x %}\n{% else %}\n{% elif y %}{% endif %}")


def test_new_mismatched_close_tags():
    assert "line 3:" in err("{% for x in xs %}\n{% if x %}\n{% endfor %}{% endif %}", {"xs": [1]})
    assert "line 2:" in err("{% if x %}\n{% endfor %}")
    assert "line 2:" in err("{% for x in xs %}\n{% endif %}")


def test_new_unclosed_blocks_report_opening_line():
    assert "line 2:" in err("a\n{% if x %}b")
    assert "line 2:" in err("{% for x in xs %}\n{% if x %}\n{% if y %}z{% endif %}")
    assert "line 1:" in err("{% for x in xs %}\n{% if x %}{% endif %}")


# ------------------------------------------------------------------ new: loop
def test_new_loop_variable():
    t = "{% for x in xs %}{{ loop.index }}/{{ loop.index0 }}/{{ loop.length }}{% if loop.first %}F{% endif %}{% if loop.last %}L{% endif %} {% endfor %}"
    assert render(t, {"xs": ["a", "b", "c"]}) == "1/0/3F 2/1/3 3/2/3L "


def test_new_loop_single_item_first_and_last():
    t = "{% for x in xs %}{% if loop.first %}F{% endif %}{% if loop.last %}L{% endif %}{% endfor %}"
    assert render(t, {"xs": [1]}) == "FL"


def test_new_loop_nested_restores_outer():
    t = ("{% for a in as_ %}{{ loop.index }}:{% for b in bs %}{{ loop.index }}{% endfor %}"
         ":{{ loop.index }}:{{ loop.length }};{% endfor %}")
    assert render(t, {"as_": [1, 2], "bs": [1, 2, 3]}) == "1:123:1:2;2:123:2:2;"


def test_new_loop_undefined_outside_and_context_loop_ok():
    assert render("{{ loop.index }}", {}) == ""
    assert "undefined" in err("{{ loop.index }}", {}, strict=True)
    assert render("{{ loop }}", {"loop": "mine"}) == "mine"
    assert render("{% for x in xs %}{% endfor %}{{ loop }}", {"xs": [1], "loop": "mine"}) == "mine"


def test_new_loop_shadows_context_variable_inside_loop():
    assert render("{% for x in xs %}{{ loop.index }}{% endfor %}", {"xs": [7, 8], "loop": {"index": "no"}}) == "12"


# ------------------------------------------------------------------ regression
def test_reg_lookup_forms():
    class Obj:
        name = "attr"

    ctx = {"d": {"k": {"n": "v"}}, "l": ["a", ["b"]], "o": Obj()}
    assert render("{{ d.k.n }}|{{ l.0 }}|{{ l.1.0 }}|{{ o.name }}", ctx) == "v|a|b|attr"
    assert render("{{ l.5 }}|{{ d.x.y }}|{{ o.nope }}", ctx) == "||"


def test_reg_none_and_undefined_print_empty():
    assert render("[{{ a }}][{{ b }}]", {"a": None}) == "[][]"
    assert render("[{{ a }}]", {"a": 0}) == "[0]"


def test_reg_escape_chars():
    assert render("{{ s }}", {"s": "&<>\"'"}) == "&amp;&lt;&gt;&quot;&#x27;"


def test_reg_safe_then_other_filter_escapes_again():
    assert render("{{ s | safe | upper }}", {"s": "<b>"}) == "&lt;B&gt;"
    assert render("{{ s | safe | trim }}", {"s": " <b> "}) == "&lt;b&gt;"
    assert render("{{ s | trim | safe }}", {"s": " <b> "}) == "<b>"


def test_reg_simple_filters():
    ctx = {"s": "  hello wORLD ", "xs": [1, 2, 3]}
    assert render("{{ s | trim | title }}", ctx) == "Hello World"
    assert render("{{ s | lower | trim }}", ctx) == "hello world"
    assert render("{{ xs | length }}|{{ s | length }}", ctx) == "3|14"
    assert render("{{ gone | length }}", {}) == "0"


def test_reg_filter_whitespace_and_text_preserved():
    assert render("  a {{x|upper}}\n{{  x  |  upper  }} b ", {"x": "q"}) == "  a Q\nQ b "


def test_reg_for_basics():
    assert render("{% for x in xs %}<{{ x }}>{% endfor %}", {"xs": []}) == ""
    assert render("{% for x in missing %}a{% endfor %}", {}) == ""
    assert render("{% for p in people %}{{ p.name }},{% endfor %}", {"people": [{"name": "a"}, {"name": "b"}]}) == "a,b,"
    assert render("{% for x in t %}{{ x }}{% endfor %}", {"t": (1, 2)}) == "12"


def test_reg_for_scope_restored():
    t = "{{ x }}{% for x in xs %}{{ x }}{% endfor %}{{ x }}"
    assert render(t, {"x": "o", "xs": [1, 2]}) == "o12o"
    assert render("{% for x in xs %}{% endfor %}[{{ x }}]", {"xs": [1]}) == "[]"
    assert render("{% for a in xs %}{% for a in ys %}{{ a }}{% endfor %}{{ a }}{% endfor %}",
                  {"xs": ["p"], "ys": ["q", "r"]}) == "qrp"


def test_reg_for_errors():
    assert "line 1:" in err("{% for x in xs %}a", {"xs": [1]})
    assert "line 2:" in err("a\n{% for x in n %}{% endfor %}", {"n": 5})
    assert "line 1:" in err("{% for x in missing %}{% endfor %}", {}, strict=True)
    assert "line 2:" in err("a\n{% endfor %}")
    assert "line 1:" in err("{% for x xs %}{% endfor %}")


def test_reg_strict_variable():
    assert "line 2:" in err("a\n{{ nope }}", strict=True)
    assert render("{{ a.b }}", {"a": {"b": 1}}, strict=True) == "1"
    assert "line 1:" in err("{{ a.b }}", {"a": {}}, strict=True)


def test_reg_comments():
    assert render("a{# hidden #}b{# multi\nline #}c", {}) == "abc"
    assert "line 2:" in err("{# one\ntwo #}{{ x | nope }}")


def test_reg_syntax_errors_with_lines():
    assert "line 2:" in err("a\n{{ x | nope }}")
    assert "line 1:" in err("{{ a b }}")
    assert "line 2:" in err("x\n{% bogus %}")
    assert "line 1:" in err("{{ }}")


def test_reg_template_error_is_exception():
    assert issubclass(TemplateError, Exception)


def test_reg_cli(tmp_path):
    t = tmp_path / "t.txt"
    t.write_text("{{ n }}", encoding="utf-8")
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"n": "<x>"}), encoding="utf-8")
    out = []
    assert main([str(t), str(d)], out.append) == 0 and out == ["&lt;x&gt;"]
    assert main([str(t)], out.append) == 2
    assert main([str(tmp_path / "none.txt"), str(d)], out.append) == 1
    assert out[-1].startswith("error:")
    t.write_text("{{ missing }}", encoding="utf-8")
    assert main([str(t), str(d)], out.append) == 0
    assert main([str(t), str(d), "--strict"], out.append) == 1
