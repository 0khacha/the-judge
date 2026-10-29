"""Recursive-descent evaluator for arithmetic expressions.

Grammar (lowest to highest precedence):

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('+' | '-') unary | power
    power   := primary ('**' unary)?          # right-associative
    primary := NUMBER | NAME | '(' expr ')'

Every failure is reported as EvalError.
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        tok = self._peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self.pos += 1
        return tok

    def _is_op(self, tok, ops):
        return tok is not None and tok.kind == "op" and tok.value in ops

    def parse(self):
        if not self.tokens:
            raise EvalError("empty expression")
        value = self._expr()
        if self._peek() is not None:
            raise EvalError("unexpected token %r" % (self._peek().value,))
        return value

    def _expr(self):
        value = self._term()
        while self._is_op(self._peek(), "+-"):
            op = self._advance().value
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._unary()
        while self._is_op(self._peek(), "*/"):
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
        if self._is_op(self._peek(), "+-"):
            op = self._advance().value
            operand = self._unary()
            return operand if op == "+" else -operand
        return self._power()

    def _power(self):
        base = self._primary()
        if self._is_op(self._peek(), ("**",)):
            self._advance()
            exponent = self._unary()
            try:
                return base ** exponent
            except ZeroDivisionError:
                raise EvalError("division by zero")
            except OverflowError:
                raise EvalError("numeric overflow")
        return base

    def _primary(self):
        tok = self._advance()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if tok.value not in self.variables:
                raise EvalError("undefined variable %r" % tok.value)
            return self.variables[tok.value]
        if tok.kind == "lparen":
            value = self._expr()
            closing = self._peek()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses")
            self._advance()
            return value
        if tok.kind == "rparen":
            raise EvalError("unbalanced parentheses")
        raise EvalError("unexpected operator %r" % (tok.value,))


def evaluate(text, variables=None):
    """Evaluate an arithmetic expression and return its numeric value.

    Supports numbers, variable names (looked up in ``variables``), parentheses,
    binary ``+ - * /``, right-associative ``**``, and unary ``+``/``-``.
    Raises EvalError for any invalid input or failed evaluation.
    """
    if variables is None:
        variables = {}
    try:
        tokens = tokenize(text)
        result = _Parser(tokens, variables).parse()
    except EvalError:
        raise
    except RecursionError:
        raise EvalError("expression nested too deeply")
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise EvalError("cannot evaluate expression: %s" % exc)

    if isinstance(result, complex):
        raise EvalError("result is not a real number")
    return result
