class IdempotentProcessor:
    def __init__(self, handler):
        self.handler = handler

    def process(self, event_id: str, payload: dict):
        return self.handler(payload)
