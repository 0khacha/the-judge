from bounded_fifo_queue import BoundedQueue

def test_queue_fifo_order():
    q = BoundedQueue(3)
    q.push(10)
    q.push(20)
    assert q.pop() == 10, "FIFO ordering violated"
