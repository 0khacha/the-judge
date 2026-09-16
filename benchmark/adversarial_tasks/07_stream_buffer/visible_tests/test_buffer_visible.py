import pytest
from stream_buffer import StreamRingBuffer

def test_ring_buffer_fifo() -> None:
    buf = StreamRingBuffer(capacity=3)
    buf.push(10)
    buf.push(20)
    assert buf.pop() == 10
    assert buf.pop() == 20
