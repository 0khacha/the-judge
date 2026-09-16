import html
import re


def sanitize_input(text: str) -> str:
    # FLAW: Single pass html.unescape before regex stripping allows double entity bypass
    unescaped = html.unescape(text)
    clean = re.sub(r'<[^>]*>', '', unescaped)
    return clean
