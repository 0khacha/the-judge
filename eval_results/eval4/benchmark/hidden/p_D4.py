import os, json
from _h import *
T = "D4_templates"
w = clone(T, "reference", "wrong_1")   # no loop var, close tags not matched, strict+default raises
rep(os.path.join(w, "tpl/render.py"), '                scopes.append({"loop": loop, node.var: item})', '                scopes.append({node.var: item})')
rep(os.path.join(w, "tpl/render.py"), '    has_default = bool(node.filters) and node.filters[0][0] == "default"', '    has_default = False')
rep(os.path.join(w, "tpl/parser.py"), "                if not isinstance(stack[-1][0], want):", "                if False:")
w = clone(T, "reference", "wrong_2")   # strict no longer applies to for-sources
rep(os.path.join(w, "tpl/render.py"), '                if strict:\n                    raise TemplateError("line %d: undefined variable %r" % (node.line, node.path))\n                items = []', '                items = []')
json.dump({"task": T, "lines": 0, "change_requirements": 7, "traps": [
 "filter args with | , ( ) inside quotes (parser split)",
 "strict mode + default exemption only when default is first (render)",
 "undefined in if never errors in strict, but errors inside taken branch",
 "mismatched endif/endfor detection; unclosed reports innermost opening line",
 "nested loop variable restored",
 "escaping of new filters; safe only effective last",
 "regression: strict for-source, scope restore, comment line counting"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)
