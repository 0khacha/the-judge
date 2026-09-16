fixed_code = '''import html
import re


def sanitize_input(text: str) -> str:
    current = text
    for _ in range(5):
        prev = current
        current = html.unescape(current)
        current = re.sub(r'<[^>]*>', '', current)
        if current == prev:
            break
    return current
'''
with open("sanitizer.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)
