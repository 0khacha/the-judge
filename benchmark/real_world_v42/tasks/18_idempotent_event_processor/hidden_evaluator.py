from idempotent_event_processor import IdempotentProcessor

def evaluate():
    side_effects = 0
    def handle_payment(p):
        nonlocal side_effects
        side_effects += 1
        return f"Processed ${p['amount']}"

    proc = IdempotentProcessor(handle_payment)
    r1 = proc.process("evt_100", {"amount": 50})
    r2 = proc.process("evt_100", {"amount": 50})
    
    assert side_effects == 1, f"Side effect count should be 1, got {side_effects}"
    assert r1 == r2 == "Processed $50"
    return True
