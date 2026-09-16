from bounded_priority_queue import BoundedPriorityQueue

def evaluate():
    q = BoundedPriorityQueue(maxsize=2)
    q.push("low", priority=1)
    q.push("high", priority=10)
    q.push("med", priority=5)
    # Queue full: "low" (p=1) should be dropped
    item1 = q.pop()
    item2 = q.pop()
    assert item1 == "high", f"Expected high, got {item1}"
    assert item2 == "med", f"Expected med, got {item2}"
    return True
