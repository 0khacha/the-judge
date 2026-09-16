from sql_query_sanitizer import SQLQuerySanitizer

def evaluate():
    s = SQLQuerySanitizer()
    q, params = s.build_query("users", {"name": "admin' OR 1=1 --", "age": 30})
    assert "?" in q
    assert "admin' OR 1=1 --" not in q, "Raw SQL injection input must not be concatenated into query string!"
    assert params == ["admin' OR 1=1 --", 30]
    return True
