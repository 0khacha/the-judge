from jwt_rbac_auth import JWTRBACManager

def evaluate():
    m = JWTRBACManager("secret")
    t1 = m.issue("user1", ["viewer"])
    t2 = m.issue("admin1", ["admin", "viewer"])
    
    assert m.authorize(t1, "viewer") is True
    assert m.authorize(t1, "admin") is False
    assert m.authorize(t2, "admin") is True
    
    m.revoke(t2)
    assert m.authorize(t2, "admin") is False, "Revoked token must be denied authorization"
    return True
