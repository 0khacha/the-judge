"""Recursive-descent evaluator for arithmetic expressions.

Grammar (lowest to highest precedence):

    expr   := term (('+' | '-') term)*
    term   := unary (('*' | '/') unary)*
    unary  := ('+' | '-') unary | power
    power  := atom ('**' unary)?          # right-associative, exponent may be signed
    atom   := number | name | '(' expr ')'

Every failure is reported as exprlib.errors.EvalError.
"""

from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize

__all__ = ["evaluate", "EvalError"]


class _Parser:
    def __init__(self, tokens, variables):
        self.tokens = tokens
        self.pos = 0
        self.variables = variables

    # -- token helpers -------------------------------------------------------
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

    # -- grammar rules -------------------------------------------------------
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
        base = self._atom()
        if self._is_op(self._peek(), "**"):
            self._next()
            exponent = self._unary()  # right-associative; may carry a sign
            return base ** exponent
        return base

    def _atom(self):
        tok = self._next()
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
            self._next()
            return value
        if tok.kind == "rparen":
            raise EvalError("unexpected ')'")
        raise EvalError("unexpected operator %r" % (tok.value,))


def evaluate(text, variables=None):
    """Evaluate an arithmetic expression and return its numeric value.

    Supports int/float literals, variables looked up in ``variables``,
    parentheses, binary ``+ - * /`` and ``**`` (right-associative), and
    unary ``+``/``-``. Raises EvalError for any invalid input or failure.
    """
    if not isinstance(text, str):
        raise EvalError("expression must be a string")
    if variables is None:
        variables = {}
    try:
        tokens = tokenize(text)
        result = _Parser(tokens, variables).parse()
    except EvalError:
        raise
    except (ZeroDivisionError, OverflowError) as exc:
        raise EvalError("arithmetic error: %s" % exc) from exc
    except RecursionError as exc:
        raise EvalError("expression nested too deeply") from exc
    except (TypeError, ValueError) as exc:
        raise EvalError("invalid expression: %s" % exc) from exc

    if isinstance(result, complex):
        raise EvalError("result is not a real number")
    return result
