import pytest
from stream_buffer import StreamRingBuffer, BufferOverflowError

def test_buffer_overflow_raises_error() -> None:
    buf = StreamRingBuffer(capacity=2)
    buf.push(1)
    buf.push(2)
    with pytest.raises(BufferOverflowError):
        buf.push(3)
