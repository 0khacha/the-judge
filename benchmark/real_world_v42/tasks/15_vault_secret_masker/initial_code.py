class SecretMasker:
    def sanitize_log(self, text: str) -> str:
        if "sk_live_" in text:
            return text.replace("sk_live_", "sk_live_***")
        return text
