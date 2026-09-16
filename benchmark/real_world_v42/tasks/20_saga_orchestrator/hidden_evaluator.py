from saga_orchestrator import SagaOrchestrator

def evaluate():
    history = []
    
    def a1(): history.append("a1")
    def c1(): history.append("c1")
    def a2(): history.append("a2")
    def c2(): history.append("c2")
    def a3(): 
        history.append("a3")
        raise RuntimeError("Step 3 failed")
    def c3(): history.append("c3")

    saga = SagaOrchestrator()
    saga.add_step(a1, c1)
    saga.add_step(a2, c2)
    saga.add_step(a3, c3)

    success = saga.execute()
    assert success is False
    assert history == ["a1", "a2", "a3", "c2", "c1"], f"Unexpected execution history: {history}"
    return True
