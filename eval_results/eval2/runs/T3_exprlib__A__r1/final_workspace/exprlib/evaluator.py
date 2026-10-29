"""Recursive-descent evaluator for arithmetic expressions.

Grammar (lowest to highest precedence)::

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('+' | '-') unary | power
    power   := primary ('**' unary)?        # right-associative, exponent may be signed
    primary := NUMBER | NAME | '(' expr ')'

Every failure is reported as ``EvalError``.
"""

import numbers

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables

    # -- token helpers -------------------------------------------------
    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self):
        tok = self._peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self.pos += 1
        return tok

    def _is_op(self, tok, *ops):
        return tok is not None and tok.kind == "op" and tok.value in ops

    # -- grammar -------------------------------------------------------
    def parse(self):
        if not self.tokens:
            raise EvalError("empty expression")
        value = self._expr()
        if self._peek() is not None:
            raise EvalError("unexpected token %r" % (self._peek().value,))
        return value

    def _expr(self):
        value = self._term()
        while self._is_op(self._peek(), "+", "-"):
            op = self._next().value
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._unary()
        while self._is_op(self._peek(), "*", "/"):
            op = self._next().value
            rhs = self._unary()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise EvalError("division by zero")
                value = value / rhs
        return value

    def _unary(self):
        if self._is_op(self._peek(), "+", "-"):
            op = self._next().value
            operand = self._unary()
            return -operand if op == "-" else +operand
        return self._power()

    def _power(self):
        base = self._primary()
        if self._is_op(self._peek(), "**"):
            self._next()
            exponent = self._unary()  # right-associative; may carry a sign
            if base == 0 and exponent < 0:
                raise EvalError("division by zero")
            return base ** exponent
        return base

    def _primary(self):
        tok = self._next()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            variables = self.variables or {}
            if tok.value not in variables:
                raise EvalError("undefined variable %r" % tok.value)
            return variables[tok.value]
        if tok.kind == "lparen":
            value = self._expr()
            closing = self._peek()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses: missing ')'")
            self.pos += 1
            return value
        if tok.kind == "rparen":
            raise EvalError("unbalanced parentheses: unexpected ')'")
        raise EvalError("unexpected token %r" % (tok.value,))


def evaluate(text, variables=None):
    """Evaluate an arithmetic expression and return its numeric value.

    ``variables`` is an optional mapping from names to numbers.
    Raises ``EvalError`` for any failure.
    """
    try:
        tokens = tokenize(text)
        result = _Parser(tokens, variables).parse()
        if not isinstance(result, numbers.Real):
            # e.g. (-8) ** 0.5 yields a complex number in Python
            raise EvalError("expression did not produce a real number")
        return result
    except EvalError:
        raise
    except Exception as exc:  # arithmetic overflow, recursion depth, etc.
        raise EvalError("cannot evaluate expression: %s" % exc) from exc
