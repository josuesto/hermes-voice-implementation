"""Length-prefixed sidecar frames: one type byte plus payload.

Frame layout on the anonymous stdin/stdout pipes:

    uint32le length | uint8 type | payload

`length` is the number of bytes after the header, including the type byte.
Control payloads are UTF-8 JSON objects with an `op` field. PCM payloads are
48 kHz stereo s16le. A 20 ms packet is 3,840 bytes. No JSON or base64 audio.
"""

from __future__ import annotations

import json
import struct
from collections.abc import Iterable

TYPE_CONTROL = 1
TYPE_PCM_IN = 2
TYPE_PCM_OUT = 3
HEADER_STRUCT = struct.Struct("<I")
MAX_FRAME_BYTES = 16384
CONTROL_OPS = frozenset({"bootstrap", "gate", "flush", "stop", "state", "error"})


class ProtocolError(ValueError):
    """Malformed, oversized, or incomplete-on-close frame."""


def encode_frame(frame_type: int, payload: bytes) -> bytes:
    if frame_type not in (TYPE_CONTROL, TYPE_PCM_IN, TYPE_PCM_OUT):
        raise ProtocolError("unsupported frame type")
    if len(payload) + 1 > MAX_FRAME_BYTES:
        raise ProtocolError("frame exceeds maximum size")
    body = bytes((frame_type,)) + payload
    return HEADER_STRUCT.pack(len(body)) + body


def encode_control(message: dict) -> bytes:
    op = message.get("op")
    if op not in CONTROL_OPS:
        raise ProtocolError("unsupported control op")
    return encode_frame(TYPE_CONTROL, json.dumps(message, separators=(",", ":")).encode("utf-8"))


def decode_control(payload: bytes) -> dict:
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("control payload is not json") from exc
    if not isinstance(message, dict) or message.get("op") not in CONTROL_OPS:
        raise ProtocolError("control payload is invalid")
    return message


class FrameDecoder:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def push(self, chunk: bytes) -> list[tuple[int, bytes]]:
        if not chunk:
            if self._buffer:
                raise ProtocolError("incomplete frame")
            return []
        self._buffer.extend(chunk)
        frames: list[tuple[int, bytes]] = []
        while True:
            if len(self._buffer) < HEADER_STRUCT.size:
                break
            (length,) = HEADER_STRUCT.unpack_from(self._buffer, 0)
            if length < 1 or length > MAX_FRAME_BYTES:
                raise ProtocolError("malformed frame length")
            need = HEADER_STRUCT.size + length
            if len(self._buffer) < need:
                break
            body = bytes(self._buffer[HEADER_STRUCT.size : need])
            del self._buffer[:need]
            frame_type = body[0]
            if frame_type not in (TYPE_CONTROL, TYPE_PCM_IN, TYPE_PCM_OUT):
                raise ProtocolError("unsupported frame type")
            frames.append((frame_type, body[1:]))
        return frames

    def close(self) -> None:
        if self._buffer:
            raise ProtocolError("incomplete frame")


def read_exact(pipe, byte_count: int) -> bytes:
    collected = bytearray()
    while len(collected) < byte_count:
        chunk = pipe.read(byte_count - len(collected))
        if not chunk:
            break
        collected.extend(chunk)
    return bytes(collected)


def read_frame(pipe) -> tuple[int, bytes] | None:
    header = read_exact(pipe, HEADER_STRUCT.size)
    if not header:
        return None
    if len(header) < HEADER_STRUCT.size:
        raise ProtocolError("incomplete frame")
    (length,) = HEADER_STRUCT.unpack(header)
    if length < 1 or length > MAX_FRAME_BYTES:
        raise ProtocolError("malformed frame length")
    body = read_exact(pipe, length)
    if len(body) < length:
        raise ProtocolError("incomplete frame")
    frame_type = body[0]
    if frame_type not in (TYPE_CONTROL, TYPE_PCM_IN, TYPE_PCM_OUT):
        raise ProtocolError("unsupported frame type")
    return frame_type, body[1:]


def iter_frames(chunks: Iterable[bytes]) -> list[tuple[int, bytes]]:
    decoder = FrameDecoder()
    frames: list[tuple[int, bytes]] = []
    for chunk in chunks:
        frames.extend(decoder.push(chunk))
    decoder.close()
    return frames
