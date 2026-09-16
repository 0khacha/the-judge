class JWTRBACManager:
    def __init__(self, secret: str):
        self.secret = secret
        self.tokens = {}
        self.revoked = set()

    def issue(self, user_id: str, roles: list) -> str:
        token = f"token_{user_id}_{len(self.tokens)}"
        self.tokens[token] = {"user": user_id, "roles": roles}
        return token

    def authorize(self, token: str, required_role: str) -> bool:
        if token in self.revoked or token not in self.tokens:
            return False
        return required_role in self.tokens[token]["roles"]

    def revoke(self, token: str):
        self.revoked.add(token)
