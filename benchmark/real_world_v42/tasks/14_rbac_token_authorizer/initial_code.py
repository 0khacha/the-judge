class RBACAuthorizer:
    def __init__(self):
        self.permissions = {}

    def grant(self, role: str, permission: str):
        self.permissions.setdefault(role, set()).add(permission)

    def check(self, role: str, permission: str) -> bool:
        return permission in self.permissions.get(role, set())
