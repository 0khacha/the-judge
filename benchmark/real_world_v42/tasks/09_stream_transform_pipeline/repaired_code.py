class StreamPipeline:
    def __init__(self):
        self.steps = []

    def add_step(self, fn):
        self.steps.append(fn)

    def process(self, records: list) -> list:
        results = []
        for r in records:
            current = dict(r)
            skip = False
            for step in self.steps:
                try:
                    res = step(current)
                    if res is None:
                        skip = True
                        break
                    current = res
                except Exception:
                    skip = True
                    break
            if not skip:
                results.append(current)
        return results
