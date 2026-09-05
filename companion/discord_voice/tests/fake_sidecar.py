"""Fake Discord sidecar for pipe and PCM tests. No Discord login."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PCM_PACKET_BYTES = 3840
from companion.discord_voice.protocol import (  # noqa: E402
    TYPE_CONTROL,
    TYPE_PCM_IN,
    TYPE_PCM_OUT,
    decode_control,
    encode_control,
    encode_frame,
    read_frame,
)

KNOWN_IN = (b"\x11\x22" * (PCM_PACKET_BYTES // 2))[:PCM_PACKET_BYTES]


def _write(frame: bytes) -> None:
    sys.stdout.buffer.write(frame)
    sys.stdout.buffer.flush()


def main() -> int:
    mode = os.environ.get("FAKE_SIDECAR_MODE", "ready")
    audience = os.environ.get("FAKE_SIDECAR_AUDIENCE", "owner_present")
    gated = False
    inbound_sent = False
    recorded: list[bytes] = []
    record_path = os.environ.get("FAKE_SIDECAR_RECORD")

    def maybe_record() -> None:
        if record_path:
            Path(record_path).write_bytes(b"".join(recorded[-8:]))

    while True:
        try:
            frame = read_frame(sys.stdin.buffer)
        except Exception:
            return 2
        if frame is None:
            break
        frame_type, payload = frame
        if frame_type == TYPE_CONTROL:
            message = decode_control(payload)
            if message["op"] == "bootstrap":
                if mode == "malformed":
                    sys.stdout.buffer.write(b"\xff\xff\xff\xff\x00")
                    sys.stdout.buffer.flush()
                    return 2
                if mode == "exit":
                    _write(
                        encode_control(
                            {
                                "op": "state",
                                "connection": "connected",
                                "audience": audience,
                            }
                        )
                    )
                    return 0
                if mode == "hold":
                    _write(
                        encode_control(
                            {
                                "op": "state",
                                "connection": "connected",
                                "audience": audience,
                            }
                        )
                    )
                    while True:
                        time.sleep(30)
                _write(
                    encode_control(
                        {
                            "op": "state",
                            "connection": "connected",
                            "audience": audience,
                        }
                    )
                )
            elif message["op"] == "gate":
                gated = message.get("audio") is True
                if gated and not inbound_sent:
                    _write(encode_frame(TYPE_PCM_IN, KNOWN_IN))
                    inbound_sent = True
                if not gated:
                    inbound_sent = False
                _write(
                    encode_control(
                        {
                            "op": "state",
                            "connection": "connected",
                            "audience": audience,
                        }
                    )
                )
            elif message["op"] == "flush":
                recorded.clear()
                maybe_record()
            elif message["op"] == "stop":
                maybe_record()
                return 0
        elif frame_type == TYPE_PCM_OUT:
            recorded.append(payload)
            maybe_record()
            if gated and os.environ.get("FAKE_SIDECAR_ECHO") == "1":
                _write(encode_frame(TYPE_PCM_IN, payload))
    maybe_record()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
