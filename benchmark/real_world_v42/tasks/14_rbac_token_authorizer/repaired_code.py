class RBACAuthorizer:
    def __init__(self):
        self.permissions = {}
        self.parents = {}

    def grant(self, role: str, permission: str):
        self.permissions.setdefault(role, set()).add(permission)

    def inherit(self, child_role: str, parent_role: str):
        self.parents.setdefault(child_role, set()).add(parent_role)

    def check(self, role: str, permission: str) -> bool:
        visited = set()
        queue = [role]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            if permission in self.permissions.get(curr, set()):
                return True
            for parent in self.parents.get(curr, set()):
                queue.append(parent)
        return False
