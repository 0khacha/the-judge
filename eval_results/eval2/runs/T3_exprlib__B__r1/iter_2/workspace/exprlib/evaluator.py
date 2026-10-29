"""Evaluate arithmetic expressions produced by exprlib.tokenizer.

Grammar (lowest precedence first)::

    expr   := term (('+' | '-') term)*
    term   := factor (('*' | '/') factor)*
    factor := ('+' | '-') factor | power
    power  := atom ['**' factor]          # right-associative, see below
    atom   := NUMBER | NAME | '(' expr ')'

Because ``power`` takes a ``factor`` as its exponent, ``2**3**2`` parses as
``2**(3**2)``, ``2**-1`` is allowed, and ``-2**2`` parses as ``-(2**2)``.
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables

    # -- token helpers -----------------------------------------------------

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _peek_op(self, *ops):
        tok = self._peek()
        return tok is not None and tok.kind == "op" and tok.value in ops

    def _advance(self):
        tok = self._peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self.pos += 1
        return tok

    # -- grammar -----------------------------------------------------------

    def parse(self):
        if not self.tokens:
            raise EvalError("empty expression")
        value = self._expr()
        tok = self._peek()
        if tok is not None:
            raise EvalError("unexpected token %r" % (tok.value,))
        return value

    def _expr(self):
        value = self._term()
        while self._peek_op("+", "-"):
            op = self._advance().value
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._factor()
        while self._peek_op("*", "/"):
            op = self._advance().value
            rhs = self._factor()
            if op == "*":
                value = value * rhs
            else:
                value = _divide(value, rhs)
        return value

    def _factor(self):
        if self._peek_op("+", "-"):
            op = self._advance().value
            operand = self._factor()
            return operand if op == "+" else -operand
        return self._power()

    def _power(self):
        base = self._atom()
        if self._peek_op("**"):
            self._advance()
            exponent = self._factor()
            return _power(base, exponent)
        return base

    def _atom(self):
        tok = self._advance()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if tok.value not in self.variables:
                raise EvalError("undefined variable %r" % tok.value)
            value = self.variables[tok.value]
            if isinstance(value, complex) or not isinstance(value, (int, float)):
                raise EvalError("variable %r is not a real number" % tok.value)
            return value
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


def _divide(lhs, rhs):
    try:
        return lhs / rhs
    except ZeroDivisionError:
        raise EvalError("division by zero")


def _power(base, exponent):
    try:
        result = base ** exponent
    except ZeroDivisionError:
        raise EvalError("division by zero")
    except OverflowError:
        raise EvalError("numeric overflow")
    if isinstance(result, complex):
        raise EvalError("result is not a real number")
    return result


def evaluate(text, variables=None):
    """Evaluate arithmetic ``text`` and return an int or float.

    ``variables`` maps variable names to numbers. Every failure (bad syntax,
    undefined variable, division by zero, illegal character) raises EvalError.
    """
    if not isinstance(text, str):
        raise EvalError("expression must be a string")
    env = {} if variables is None else variables
    tokens = tokenize(text)
    try:
        return _Parser(tokens, env).parse()
    except RecursionError:
        raise EvalError("expression nested too deeply")
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise EvalError("cannot evaluate expression: %s" % exc)
