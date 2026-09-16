class IdempotentProcessor:
    def __init__(self, handler):
        self.handler = handler
        self.processed = {}

    def process(self, event_id: str, payload: dict):
        if event_id in self.processed:
            return self.processed[event_id]
        res = self.handler(payload)
        self.processed[event_id] = res
        return res
