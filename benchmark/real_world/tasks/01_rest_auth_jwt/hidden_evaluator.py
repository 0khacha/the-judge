import time
from jwt_token_manager import JWTTokenManager

def test_jwt_issuance_and_revocation():
    m = JWTTokenManager("secret", ttl_seconds=0.2)
    t1 = m.issue_token("user1")
    assert m.validate_token(t1) is True
    m.revoke_token(t1)
    assert m.validate_token(t1) is False

def test_jwt_expiration():
    m = JWTTokenManager("secret", ttl_seconds=0.1)
    t1 = m.issue_token("user2")
    assert m.validate_token(t1) is True
    time.sleep(0.15)
    assert m.validate_token(t1) is False, "Expired token must be rejected"
