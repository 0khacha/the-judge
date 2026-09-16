from finite_state_machine import StateMachine
import pytest

def evaluate():
    sm = StateMachine(initial_state="draft")
    sm.add_transition("draft", "submitted", "submit", guard=lambda: True)
    sm.add_transition("submitted", "approved", "approve", guard=lambda: False)
    
    sm.trigger("submit")
    assert sm.state == "submitted"
    
    try:
        sm.trigger("approve")
    except ValueError:
        pass
    assert sm.state == "submitted", f"State should remain 'submitted' on guard failure, got {sm.state}"
    return True
