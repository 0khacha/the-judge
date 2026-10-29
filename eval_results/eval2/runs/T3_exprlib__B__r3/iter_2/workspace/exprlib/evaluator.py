"""Recursive-descent evaluator for arithmetic expressions.

Grammar (lowest to highest precedence)::

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('+' | '-') unary | power
    power   := primary ('**' unary)?          # right-associative, Python-style
    primary := NUMBER | NAME | '(' expr ')'

Every failure is reported as ``EvalError``.
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self._tokens = tokens
        self._pos = 0
        self._variables = variables

    def _peek(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self):
        tok = self._peek()
        self._pos += 1
        return tok

    @staticmethod
    def _is_op(tok, *ops):
        return tok is not None and tok.kind == "op" and tok.value in ops

    def parse(self):
        if not self._tokens:
            raise EvalError("empty expression")
        value = self._expr()
        leftover = self._peek()
        if leftover is not None:
            raise EvalError("unexpected token %r" % (leftover.value,))
        return value

    def _expr(self):
        value = self._term()
        while self._is_op(self._peek(), "+", "-"):
            op = self._advance().value
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._unary()
        while self._is_op(self._peek(), "*", "/"):
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
        if self._is_op(self._peek(), "+", "-"):
            op = self._advance().value
            operand = self._unary()
            return operand if op == "+" else -operand
        return self._power()

    def _power(self):
        base = self._primary()
        if self._is_op(self._peek(), "**"):
            self._advance()
            exponent = self._unary()  # exponent may carry a unary sign
            if base == 0 and exponent < 0:
                raise EvalError("division by zero")
            result = base ** exponent
            if isinstance(result, complex):
                raise EvalError("result is not a real number")
            return result
        return base

    def _primary(self):
        tok = self._advance()
        if tok is None:
            raise EvalError("unexpected end of expression")
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if tok.value not in self._variables:
                raise EvalError("undefined variable %r" % tok.value)
            value = self._variables[tok.value]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EvalError("variable %r is not a number" % tok.value)
            return value
        if tok.kind == "lparen":
            value = self._expr()
            closing = self._advance()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses")
            return value
        raise EvalError("unexpected token %r" % (tok.value,))


def evaluate(text, variables=None):
    """Evaluate an arithmetic expression and return an int or float.

    ``variables`` maps names to numbers. Raises ``EvalError`` for any problem.
    """
    if not isinstance(text, str):
        raise EvalError("expression must be a string")
    if variables is None:
        variables = {}
    try:
        tokens = tokenize(text)
        return _Parser(tokens, variables).parse()
    except (ArithmeticError, RecursionError, ValueError) as exc:
        raise EvalError(str(exc)) from exc
