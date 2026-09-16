class SessionStore:
    def __init__(self):
        self.sessions = {}

    def create_session(self, user_id: str) -> str:
        sid = f"sess_{user_id}"
        self.sessions[sid] = user_id
        return sid

    def get_session(self, sid: str):
        return self.sessions.get(sid)

    def destroy_session(self, sid: str):
        # BUG: Fails to remove session key from self.sessions dictionary
        pass
