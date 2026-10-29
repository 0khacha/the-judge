"""Evaluate arithmetic expressions over numbers and named variables.

Grammar (lowest to highest precedence)::

    expr    := term (('+' | '-') term)*          left-associative
    term    := unary (('*' | '/') unary)*        left-associative
    unary   := ('+' | '-') unary | power         unary binds looser than '**'
    power   := primary ('**' unary)?             right-associative
    primary := NUMBER | NAME | '(' expr ')'

Every failure is reported as ``EvalError``.
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]

# Upper bound on the estimated bit size of an integer power result, so that
# expressions such as ``2 ** 10**12`` fail fast instead of exhausting memory.
_MAX_INT_RESULT_BITS = 1000000


class _Parser:
    def __init__(self, tokens, variables):
        self._tokens = tokens
        self._pos = 0
        self._variables = variables

    # -- token helpers -----------------------------------------------------

    def _peek(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _next(self):
        tok = self._peek()
        if tok is None:
            raise EvalError("unexpected end of expression")
        self._pos += 1
        return tok

    def _at_op(self, *ops):
        tok = self._peek()
        return tok is not None and tok.kind == "op" and tok.value in ops

    # -- grammar -----------------------------------------------------------

    def parse(self):
        if not self._tokens:
            raise EvalError("empty expression")
        value = self._expr()
        tok = self._peek()
        if tok is not None:
            if tok.kind == "rparen":
                raise EvalError("unbalanced parentheses")
            raise EvalError("unexpected token %r" % (tok.value,))
        return value

    def _expr(self):
        value = self._term()
        while self._at_op("+", "-"):
            op = self._next().value
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._unary()
        while self._at_op("*", "/"):
            op = self._next().value
            rhs = self._unary()
            value = _mul(value, rhs) if op == "*" else _div(value, rhs)
        return value

    def _unary(self):
        if self._at_op("+", "-"):
            op = self._next().value
            operand = self._unary()
            return operand if op == "+" else -operand
        return self._power()

    def _power(self):
        base = self._primary()
        if self._at_op("**"):
            self._next()
            exponent = self._unary()  # right-associative; may carry a sign
            return _pow(base, exponent)
        return base

    def _primary(self):
        tok = self._next()
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            try:
                return self._variables[tok.value]
            except KeyError:
                raise EvalError("undefined variable %r" % tok.value) from None
        if tok.kind == "lparen":
            value = self._expr()
            closing = self._peek()
            if closing is None or closing.kind != "rparen":
                raise EvalError("unbalanced parentheses")
            self._pos += 1
            return value
        if tok.kind == "rparen":
            raise EvalError("unbalanced parentheses")
        raise EvalError("unexpected operator %r" % (tok.value,))


def _mul(a, b):
    try:
        return a * b
    except OverflowError:
        raise EvalError("numeric overflow") from None


def _div(a, b):
    if b == 0:
        raise EvalError("division by zero")
    try:
        return a / b
    except OverflowError:
        raise EvalError("numeric overflow") from None


def _pow(base, exponent):
    if base == 0 and exponent < 0:
        raise EvalError("division by zero")
    if (
        isinstance(base, int)
        and isinstance(exponent, int)
        and abs(base) > 1
        and exponent > 0
        and abs(base).bit_length() * exponent > _MAX_INT_RESULT_BITS
    ):
        raise EvalError("result too large")
    try:
        result = base ** exponent
    except OverflowError:
        raise EvalError("numeric overflow") from None
    except ZeroDivisionError:
        raise EvalError("division by zero") from None
    if isinstance(result, complex):
        raise EvalError("result is not a real number")
    return result


def evaluate(text, variables=None):
    """Evaluate arithmetic expression ``text`` and return the numeric result.

    ``variables`` maps names used in the expression to numeric values.
    Raises ``EvalError`` for any invalid input or failed evaluation.
    """
    if variables is None:
        variables = {}
    try:
        tokens = tokenize(text)
        return _Parser(tokens, variables).parse()
    except EvalError:
        raise
    except RecursionError:
        raise EvalError("expression nested too deeply") from None
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise EvalError(str(exc)) from None
