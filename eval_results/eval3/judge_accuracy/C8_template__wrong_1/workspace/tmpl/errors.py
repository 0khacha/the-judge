class TemplateError(Exception):
    """Raised for any template syntax error. `line` is the 1-based line number (or None)."""

    def __init__(self, message, line=None):
        super().__init__(message if line is None else "line %d: %s" % (line, message))
        self.message = message
        self.line = line
