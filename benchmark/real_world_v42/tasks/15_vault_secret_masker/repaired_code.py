import re

class SecretMasker:
    def sanitize_log(self, text: str) -> str:
        # Mask API keys
        s = re.sub(r'sk_live_[a-zA-Z0-9]+', '[REDACTED_KEY]', text)
        # Mask Credit Cards (13-19 digits with optional hyphens/spaces)
        s = re.sub(r'\b(?:\d[ -]*?){13,19}\b', '[REDACTED_CC]', s)
        return s
