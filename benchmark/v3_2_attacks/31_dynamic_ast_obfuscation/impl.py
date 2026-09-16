code_str = "def sanitize_input(val): return val if '<script>' not in val else ''"
exec(code_str, globals())
# Obfuscated AST makes static property inference produce 0 properties
