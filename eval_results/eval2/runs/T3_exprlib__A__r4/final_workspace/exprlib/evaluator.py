"""Evaluate arithmetic expressions.

Grammar (lowest to highest precedence):

    expr    := term (('+' | '-') term)*
    term    := unary (('*' | '/') unary)*
    unary   := ('+' | '-') unary | power
    power   := primary ('**' unary)?        # right-associative, exponent may be signed
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
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self):
        tok = self._peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self.pos += 1
        return tok

    def _is_op(self, tok, *ops):
        return tok is not None and tok.kind == "op" and tok.value in ops

    def parse(self):
        if not self.tokens:
            raise EvalError("empty expression")
        value = self._expr()
        leftover = self._peek()
        if leftover is not None:
            if leftover.kind == "rparen":
                raise EvalError("unbalanced parentheses")
            raise EvalError("unexpected token %r" % (leftover.value,))
        return value

    def _expr(self):
        value = self._term()
        while self._is_op(self._peek(), "+", "-"):
            op = self._advance().value
            right = self._term()
            value = value + right if op == "+" else value - right
        return value

    def _term(self):
        value = self._unary()
        while self._is_op(self._peek(), "*", "/"):
            op = self._advance().value
            right = self._unary()
            if op == "*":
                value = value * right
            else:
                if right == 0:
                    raise EvalError("division by zero")
                value = value / right
        return value

    def _unary(self):
        if self._is_op(self._peek(), "+", "-"):
            op = self._advance().value
            operand = self._unary()
            return -operand if op == "-" else +operand
        return self._power()

    def _power(self):
        base = self._primary()
        if self._is_op(self._peek(), "**"):
            self._advance()
            exponent = self._unary()  # right-associative; allows a signed exponent
            if base == 0 and exponent < 0:
                raise EvalError("division by zero")
            result = base ** exponent
            if isinstance(result, complex):
                raise EvalError("result is not a real number")
            return result
        return base

    def _primary(self):
        tok = self._advance()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if tok.value not in self.variables:
                raise EvalError("undefined variable %r" % tok.value)
            value = self.variables[tok.value]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EvalError("variable %r is not a number" % tok.value)
            return value
        if tok.kind == "lparen":
            value = self._expr()
            closing = self._peek()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses")
            self._advance()
            return value
        if tok.kind == "rparen":
            raise EvalError("unexpected ')'")
        raise EvalError("unexpected operator %r" % (tok.value,))


def evaluate(text, variables=None):
    """Evaluate arithmetic ``text`` and return an int or float.

    ``variables`` maps names to numbers. Raises EvalError on any failure.
    """
    if variables is None:
        variables = {}
    try:
        tokens = tokenize(text)
        if not tokens:
            raise EvalError("empty expression")
        return _Parser(tokens, variables).parse()
    except EvalError:
        raise
    except ZeroDivisionError:
        raise EvalError("division by zero") from None
    except RecursionError:
        raise EvalError("expression nested too deeply") from None
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise EvalError("cannot evaluate expression: %s" % exc) from None
