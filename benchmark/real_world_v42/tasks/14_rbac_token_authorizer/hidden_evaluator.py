from rbac_token_authorizer import RBACAuthorizer

def evaluate():
    rbac = RBACAuthorizer()
    rbac.grant("viewer", "read")
    rbac.grant("editor", "write")
    rbac.inherit("editor", "viewer")
    rbac.inherit("admin", "editor")
    
    assert rbac.check("viewer", "read") is True
    assert rbac.check("viewer", "write") is False
    assert rbac.check("admin", "write") is True
    assert rbac.check("admin", "read") is True, "Admin should inherit viewer read permission via editor"
    return True
