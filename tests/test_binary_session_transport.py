import io

import pytest

pytestmark = pytest.mark.experimental


def test_binary_transport_frame_roundtrip():
    from vermyth.mcp.binary_transport import FrameType, decode_frame_from_buffer, encode_frame

    payload = b'{"hello":"world"}'
    data = encode_frame(FrameType.SESSION_OPEN, payload)
    buf = io.BufferedReader(io.BytesIO(data))
    frame = decode_frame_from_buffer(buf)
    assert frame is not None
    assert frame.frame_type == FrameType.SESSION_OPEN
    assert frame.payload == payload

