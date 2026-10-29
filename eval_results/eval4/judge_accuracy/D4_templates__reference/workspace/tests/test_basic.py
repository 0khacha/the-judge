import json

import pytest

from tpl import TemplateError, render
from tpl.cli import main


def test_plain_and_var():
    assert render("Hi {{ name }}!", {"name": "Ann"}) == "Hi Ann!"


def test_dotted_and_index():
    ctx = {"u": {"tags": ["a", "b"]}}
    assert render("{{ u.tags.1 }}", ctx) == "b"


def test_filters():
    assert render("{{ n | trim | upper }}", {"n": "  ab "}) == "AB"
    assert render("{{ xs | length }}", {"xs": [1, 2, 3]}) == "3"


def test_escape_and_safe():
    assert render("{{ x }}", {"x": "<b>"}) == "&lt;b&gt;"
    assert render("{{ x | safe }}", {"x": "<b>"}) == "<b>"


def test_for():
    assert render("{% for x in xs %}[{{ x }}]{% endfor %}", {"xs": [1, 2]}) == "[1][2]"


def test_unknown_filter_error():
    with pytest.raises(TemplateError) as e:
        render("a\n{{ x | nope }}", {})
    assert "line 2" in str(e.value)


def test_strict():
    with pytest.raises(TemplateError):
        render("{{ x }}", {}, strict=True)
    assert render("{{ x }}", {}) == ""


def test_cli(tmp_path):
    t = tmp_path / "t.txt"
    t.write_text("Hi {{ n }}", encoding="utf-8")
    d = tmp_path / "d.json"
    d.write_text(json.dumps({"n": "Bo"}), encoding="utf-8")
    out = []
    assert main([str(t), str(d)], out.append) == 0
    assert out == ["Hi Bo"]
