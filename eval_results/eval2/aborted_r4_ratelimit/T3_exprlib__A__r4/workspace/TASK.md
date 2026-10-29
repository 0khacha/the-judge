# T3: expression evaluator (extend existing package)

The package `exprlib/` already exists (`errors.py` with `EvalError`, `tokenizer.py` with `tokenize`). Do not break them. Create `exprlib/evaluator.py` providing:

- `evaluate(text, variables=None)` -> number. Evaluates an arithmetic expression using `exprlib.tokenizer.tokenize`.
- `EvalError` importable from `exprlib.evaluator` (the same class as `exprlib.errors.EvalError`).

Grammar / semantics:
- Numbers (int or float), variable names (looked up in the `variables` dict), parentheses.
- Binary `+ - * /` (left-associative; `*` `/` bind tighter than `+` `-`); `/` is true division.
- `**` is exponentiation and is RIGHT-associative: `2**3**2 == 512`.
- Unary `+` and `-` are allowed. Exponentiation binds tighter than a unary operator on its left, as in Python: `-2**2 == -4`. An exponent may itself carry a unary sign: `2**-1 == 0.5`. Repeated unary is fine: `--3 == 3`, `2 - -3 == 5`.
- Every failure raises `EvalError` (never a raw Python exception): empty input, unbalanced parentheses, dangling operator (`"1 +"`), two adjacent operands (`"1 2"`), undefined variable, division by zero (including `0 ** -1`), illegal characters.
