class SagaOrchestrator:
    def __init__(self):
        self.steps = []

    def add_step(self, action, compensate):
        self.steps.append((action, compensate))

    def execute(self) -> bool:
        executed = []
        for action, compensate in self.steps:
            try:
                action()
                executed.append(compensate)
            except Exception as e:
                # Rollback in reverse order
                for comp in reversed(executed):
                    try:
                        comp()
                    except Exception:
                        pass
                return False
        return True
