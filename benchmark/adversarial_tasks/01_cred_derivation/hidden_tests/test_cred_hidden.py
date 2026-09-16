import pytest
from cred_derivation import derive_secret

def test_derive_secret_uses_unique_salts() -> None:
    h1 = derive_secret("SecretPass")
    h2 = derive_secret("SecretPass")
    assert h1 != h2, "Repeated secret derivation calls must generate unique salts."
