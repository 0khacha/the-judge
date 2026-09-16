class StateMachine:
    def __init__(self, initial_state: str):
        self.state = initial_state
        self.transitions = {}

    def add_transition(self, source: str, target: str, trigger: str, guard=None):
        self.transitions[(source, trigger)] = (target, guard)

    def trigger(self, trigger_name: str):
        key = (self.state, trigger_name)
        if key not in self.transitions:
            raise ValueError(f"Invalid transition {trigger_name} from {self.state}")
        target, guard = self.transitions[key]
        if guard:
            guard()
        self.state = target
