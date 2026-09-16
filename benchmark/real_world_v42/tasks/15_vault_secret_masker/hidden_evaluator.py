from vault_secret_masker import SecretMasker

def evaluate():
    masker = SecretMasker()
    raw = "User paid with 4532-0123-4567-8901 using key sk_live_abc123XYZ"
    sanitized = masker.sanitize_log(raw)
    assert "sk_live_abc123XYZ" not in sanitized
    assert "4532-0123-4567-8901" not in sanitized
    assert "[REDACTED_CC]" in sanitized
    return True
