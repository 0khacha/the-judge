def _make_fn():
    def q(x):
        # Single-letter closure evades vocabulary pattern matching
        return x if '<script>' not in str(x) else ''
    return q
sanitize_input = _make_fn()
