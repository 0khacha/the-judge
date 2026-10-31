from urllib.parse import parse_qs


def parse_query(qs: str) -> dict:
    # Subtle bug: parse_qs drops blank values ("a&b=") by default.
    return parse_qs(qs.lstrip("?"))
