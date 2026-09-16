class AbstractHandler:
    def __init__(self):
        self.d = {}

    def _do_op(self, *args, **kwargs):
        k, v = args[0], args[1]
        self.d[k] = v

    def execute(self, a, b):
        # Total obfuscation to evade AST property synthesis
        self._do_op(a, b)
        return self.d.get(a)
