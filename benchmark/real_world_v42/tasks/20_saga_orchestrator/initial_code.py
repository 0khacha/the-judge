class SagaOrchestrator:
    def __init__(self):
        self.steps = []

    def add_step(self, action, compensate):
        self.steps.append((action, compensate))

    def execute(self):
        for action, compensate in self.steps:
            action()
