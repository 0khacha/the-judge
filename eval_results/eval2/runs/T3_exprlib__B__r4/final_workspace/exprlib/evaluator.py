"""Recursive-descent evaluator for arithmetic expressions.

Grammar (lowest to highest precedence)::

    expr    := term (('+' | '-') term)*
    term    := factor (('*' | '/') factor)*
    factor  := ('+' | '-') factor | power
    power   := primary ('**' factor)?
    primary := NUMBER | NAME | '(' expr ')'

``**`` is right-associative and its exponent is a ``factor``, so it may carry a
unary sign (``2**-1``). Unary signs bind looser than ``**`` (``-2**2 == -4``).
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        tok = self.peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self.pos += 1
        return tok

    def is_op(self, tok, *ops):
        return tok is not None and tok.kind == "op" and tok.value in ops

    def parse(self):
        if not self.tokens:
            raise EvalError("empty expression")
        value = self.expr()
        if self.peek() is not None:
            raise EvalError("unexpected token %r" % (self.peek().value,))
        return value

    def expr(self):
        value = self.term()
        while self.is_op(self.peek(), "+", "-"):
            op = self.advance().value
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self):
        value = self.factor()
        while self.is_op(self.peek(), "*", "/"):
            op = self.advance().value
            rhs = self.factor()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise EvalError("division by zero")
                value = value / rhs
        return value

    def factor(self):
        if self.is_op(self.peek(), "+", "-"):
            op = self.advance().value
            operand = self.factor()
            return -operand if op == "-" else +operand
        return self.power()

    def power(self):
        base = self.primary()
        if self.is_op(self.peek(), "**"):
            self.advance()
            exponent = self.factor()  # right-associative; allows unary sign
            if base == 0 and exponent < 0:
                raise EvalError("0 cannot be raised to a negative power")
            result = base ** exponent
            if isinstance(result, complex):
                raise EvalError("result is not a real number")
            return result
        return base

    def primary(self):
        tok = self.advance()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if self.variables is None or tok.value not in self.variables:
                raise EvalError("undefined variable %r" % tok.value)
            return self.variables[tok.value]
        if tok.kind == "lparen":
            value = self.expr()
            closing = self.peek()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses: missing ')'")
            self.advance()
            return value
        if tok.kind == "rparen":
            raise EvalError("unbalanced parentheses: unexpected ')'")
        raise EvalError("unexpected operator %r" % (tok.value,))


def evaluate(text, variables=None):
    """Evaluate an arithmetic expression and return a number.

    Variables are looked up in the optional ``variables`` mapping. Every failure
    raises ``EvalError``.
    """
    if not isinstance(text, str):
        raise EvalError("expression must be a string")
    tokens = tokenize(text)
    try:
        return _Parser(tokens, variables).parse()
    except EvalError:
        raise
    except (ZeroDivisionError, OverflowError, ValueError, TypeError) as exc:
        raise EvalError(str(exc)) from exc
