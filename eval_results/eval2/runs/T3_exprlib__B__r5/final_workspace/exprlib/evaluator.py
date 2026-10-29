"""Arithmetic expression evaluator built on exprlib.tokenizer.

Grammar (lowest to highest precedence)::

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('+' | '-') unary | power
    power   := primary ('**' unary)?          # right-associative, exponent may be signed
    primary := NUMBER | NAME | '(' expr ')'

Unary minus binds looser than ``**`` so that ``-2**2 == -4``, as in Python.
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self._tokens = tokens
        self._pos = 0
        self._variables = variables

    # -- token helpers -------------------------------------------------
    def _peek(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self):
        tok = self._peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self._pos += 1
        return tok

    def _at_op(self, *ops):
        tok = self._peek()
        return tok is not None and tok.kind == "op" and tok.value in ops

    # -- grammar -------------------------------------------------------
    def parse(self):
        if not self._tokens:
            raise EvalError("empty expression")
        value = self._expr()
        if self._peek() is not None:
            raise EvalError("unexpected token %r" % (self._peek().value,))
        return value

    def _expr(self):
        value = self._term()
        while self._at_op("+", "-"):
            op = self._advance().value
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._unary()
        while self._at_op("*", "/"):
            op = self._advance().value
            rhs = self._unary()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise EvalError("division by zero")
                value = value / rhs
        return value

    def _unary(self):
        if self._at_op("+", "-"):
            op = self._advance().value
            operand = self._unary()
            return -operand if op == "-" else +operand
        return self._power()

    def _power(self):
        base = self._primary()
        if self._at_op("**"):
            self._advance()
            exponent = self._unary()  # right-associative; allows signed exponent
            if base == 0 and exponent < 0:
                raise EvalError("0 cannot be raised to a negative power")
            return base ** exponent
        return base

    def _primary(self):
        tok = self._advance()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if tok.value not in self._variables:
                raise EvalError("undefined variable %r" % tok.value)
            return self._variables[tok.value]
        if tok.kind == "lparen":
            value = self._expr()
            closing = self._peek()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses: missing ')'")
            self._advance()
            return value
        if tok.kind == "rparen":
            raise EvalError("unbalanced parentheses: unexpected ')'")
        raise EvalError("unexpected token %r" % (tok.value,))


def _check_variables(variables):
    if variables is None:
        return {}
    if not isinstance(variables, dict):
        raise EvalError("variables must be a dict")
    for name, value in variables.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EvalError("variable %r is not a number" % (name,))
    return variables


def evaluate(text, variables=None):
    """Evaluate an arithmetic expression and return its numeric value.

    Raises EvalError for any problem (empty input, syntax errors, undefined
    variables, division by zero, overflow, illegal characters).
    """
    if not isinstance(text, str):
        raise EvalError("expression must be a string")
    env = _check_variables(variables)
    try:
        tokens = tokenize(text)
        result = _Parser(tokens, env).parse()
    except EvalError:
        raise
    except ZeroDivisionError as exc:
        raise EvalError("division by zero") from exc
    except RecursionError as exc:
        raise EvalError("expression nested too deeply") from exc
    except (ArithmeticError, ValueError, TypeError) as exc:
        raise EvalError("cannot evaluate expression: %s" % exc) from exc
    if isinstance(result, complex):
        raise EvalError("result is not a real number")
    return result
