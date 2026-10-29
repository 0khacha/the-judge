from tmpl import render, TemplateError


def test_variable_and_escape():
    assert render("Hi {{ name }}!", {"name": "<b>"}) == "Hi &lt;b&gt;!"


def test_for_loop():
    assert render("{% for x in xs %}[{{ x }}]{% endfor %}", {"xs": [1, 2]}) == "[1][2]"


def test_if_else():
    assert render("{% if a %}y{% else %}n{% endif %}", {"a": 0}) == "n"
