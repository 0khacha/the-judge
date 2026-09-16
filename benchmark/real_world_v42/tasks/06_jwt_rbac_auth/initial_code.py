class JWTRBACManager:
    def __init__(self, secret: str):
        self.secret = secret
        self.tokens = {}

    def issue(self, user_id: str, roles: list) -> str:
        token = f"token_{user_id}"
        self.tokens[token] = {"user": user_id, "roles": roles}
        return token

    def authorize(self, token: str, required_role: str) -> bool:
        if token not in self.tokens:
            return False
        return required_role in self.tokens[token]["roles"]

    def revoke(self, token: str):
        pass
