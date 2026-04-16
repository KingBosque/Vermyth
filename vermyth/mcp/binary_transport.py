"""Binary-first session transport (framed bytes over stdio).

This is an additive transport that can coexist with the current JSON-RPC mode.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass


MAGIC = b"VMTH"
VERSION = 1


class FrameType:
    SESSION_OPEN = 1
    SESSION_ACK = 2
    SESSION_CLOSE = 3
    PACKET = 10
    RESPONSE = 11
    GOSSIP_PUSH = 20
    GOSSIP_PULL = 21
    GOSSIP_ACK = 22
    CAUSAL_SYNC = 30
    ERROR = 255


@dataclass(frozen=True)
class BinaryFrame:
    frame_type: int
    payload: bytes


def encode_frame(frame_type: int, payload: bytes) -> bytes:
    # Header: MAGIC(4) VERSION(1) TYPE(1) LEN(4 big-endian)
    header = MAGIC + struct.pack(">BBI", VERSION, int(frame_type) & 0xFF, len(payload))
    return header + payload


def decode_frame_from_buffer(buf: io.BufferedReader) -> BinaryFrame | None:
    header = buf.read(10)
    if not header:
        return None
    if len(header) != 10:
        raise ValueError("incomplete frame header")
    magic = header[:4]
    if magic != MAGIC:
        raise ValueError("invalid magic")
    version, frame_type, length = struct.unpack(">BBI", header[4:])
    if version != VERSION:
        raise ValueError("unsupported binary transport version")
    payload = buf.read(int(length))
    if len(payload) != int(length):
        raise ValueError("incomplete frame payload")
    return BinaryFrame(frame_type=int(frame_type), payload=payload)

