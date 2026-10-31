from exprlib.errors import EvalError
from exprlib.tokenizer import tokenize


class _Parser:
    def __init__(self, tokens, variables):
        self.t = tokens
        self.i = 0
        self.vars = variables

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def op(self, *ops):
        tok = self.peek()
        if tok and tok.kind == "op" and tok.value in ops:
            self.i += 1
            return tok.value
        return None

    def expr(self):
        v = self.term()
        while True:
            o = self.op("+", "-")
            if not o:
                return v
            r = self.term()
            v = v + r if o == "+" else v - r

    def term(self):
        v = self.unary()
        while True:
            o = self.op("*", "/")
            if not o:
                return v
            r = self.unary()
            if o == "*":
                v = v * r
            else:
                if r == 0:
                    raise ZeroDivisionError("division by zero")
                v = v / r

    def unary(self):
        o = self.op("+", "-")
        if o:
            v = self.unary()
            return -v if o == "-" else v
        return self.power()

    def power(self):
        base = self.atom()
        if self.op("**"):
            exp = self.unary()
            try:
                r = base ** exp
            except ZeroDivisionError:
                raise ZeroDivisionError("division by zero")
            except OverflowError:
                raise EvalError("overflow")
            if isinstance(r, complex):
                raise EvalError("complex result")
            return r
        return base

    def atom(self):
        tok = self.peek()
        if tok is None:
            raise EvalError("unexpected end")
        self.i += 1
        if tok.kind == "num":
            return tok.value
        if tok.kind == "name":
            if tok.value not in self.vars:
                raise KeyError(tok.value)
            return self.vars[tok.value]
        if tok.kind == "lparen":
            v = self.expr()
            nxt = self.peek()
            if not nxt or nxt.kind != "rparen":
                raise EvalError("expected )")
            self.i += 1
            return v
        raise EvalError("unexpected token")


def evaluate(text, variables=None):
    p = _Parser(tokenize(text), variables or {})
    v = p.expr()
    if p.peek() is not None:
        raise EvalError("unexpected trailing input")
    return v
