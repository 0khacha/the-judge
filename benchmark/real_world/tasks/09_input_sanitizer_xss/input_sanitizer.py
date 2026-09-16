def sanitize_html(raw_html: str) -> str:
    # BUG: Single pass replacement of <script> breaks on uppercase or unclosed tags
    return raw_html.replace("<script>", "").replace("</script>", "")
