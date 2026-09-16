class StreamPipeline:
    def __init__(self):
        self.steps = []

    def add_step(self, fn):
        self.steps.append(fn)

    def process(self, records: list) -> list:
        results = []
        for r in records:
            for step in self.steps:
                r = step(r)
            results.append(r)
        return results
