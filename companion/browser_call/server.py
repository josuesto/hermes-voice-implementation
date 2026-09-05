"""One-peer WebRTC bridge between a browser and Codex Voice.

This prototype keeps SDP and audio in memory, serves no diagnostics containing
addresses, and defaults to loopback-only HTTP. Non-loopback serving requires TLS.
Browser audio goes to VB-CABLE. Return audio is captured from the unique
current-session Codex process tree, never from system-wide loopback.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import ssl
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError
from av import AudioFrame
from av.audio.resampler import AudioResampler

from companion.audio_io import (
    CABLE_INPUT_NAME,
    FRAME_SAMPLES,
    HELPER_BUILD_SCRIPT,
    HELPER_EXE,
    HELPER_SOURCE,
    PCM_BUFFER_LIMIT,
    PCM_BYTES_PER_FRAME,
    SAMPLE_RATE,
    CableAudioSink as PcmCableAudioSink,
    ProcessLoopbackSource,
    ensure_process_loopback_helper,
    find_unique_codex_process,
    pick_unique_codex_process,
    pick_wasapi_output,
)

MAX_OFFER_BYTES = 131072
_BROWSER_DIR = Path(__file__).resolve().parent
STATIC_DIR = _BROWSER_DIR / "static"
AUDIO_RECEIVING_PEAK = 0.01
PEER_STATES = frozenset({"none", "connecting", "connected", "failed"})
BROWSER_AUDIO_STATES = frozenset({"no-peer", "silent", "receiving"})
CABLE_STATES = frozenset({"inactive", "forwarding", "failed"})


def classify_peer_state(connection_state: str | None) -> str:
    if connection_state is None:
        return "none"
    if connection_state == "connected":
        return "connected"
    if connection_state in ("failed", "closed", "disconnected"):
        return "failed"
    return "connecting"


def classify_browser_audio(has_peer: bool, peak: float) -> str:
    if not has_peer:
        return "no-peer"
    if float(peak) >= AUDIO_RECEIVING_PEAK:
        return "receiving"
    return "silent"


def classify_cable(*, failed: bool, forwarding: bool) -> str:
    if failed:
        return "failed"
    if forwarding:
        return "forwarding"
    return "inactive"


def pick_wasapi_output(devices: Any, hostapis: Any, name: str = CABLE_INPUT_NAME) -> int:
    matches: list[int] = []
    for index, device in enumerate(devices):
        try:
            hostapi = hostapis[int(device["hostapi"])]
            if (
                str(hostapi["name"]) == "Windows WASAPI"
                and str(device["name"]) == name
                and int(device["max_output_channels"]) > 0
            ):
                matches.append(index)
        except (IndexError, KeyError, TypeError, ValueError):
            continue
    if len(matches) != 1:
        raise RuntimeError("exactly one standard VB-CABLE WASAPI output is required")
    return matches[0]


class CableAudioSink(PcmCableAudioSink):
    """Consume one browser track and write float PCM to CABLE Input."""

    async def consume(self, track: MediaStreamTrack) -> None:
        try:
            self.open()
        except Exception:
            self.failed = True
            raise
        resampler = AudioResampler(format="fltp", layout="stereo", rate=SAMPLE_RATE)
        try:
            while True:
                frame = await track.recv()
                for converted in resampler.resample(frame):
                    audio = converted.to_ndarray().astype(np.float32, copy=False)
                    if audio.ndim != 2:
                        raise RuntimeError("unsupported browser audio shape")
                    packed = np.ascontiguousarray(audio.T)
                    await asyncio.to_thread(self.write_float, packed)
        except (MediaStreamError, asyncio.CancelledError):
            raise
        except Exception:
            self.failed = True
            raise
        finally:
            self.close()


class CodexProcessAudioTrack(MediaStreamTrack):
    """Timed 48 kHz Codex-only PCM, plus an explicit short test tone."""

    kind = "audio"

    def __init__(self, source=None, source_factory=ProcessLoopbackSource) -> None:
        super().__init__()
        self._owns_source = source is None
        self._source = source if source is not None else source_factory()
        if self._owns_source:
            self._source.start()
        self._pts = 0
        self._next_at: float | None = None
        self._tone_until = 0.0

    def trigger(self, seconds: float = 1.0) -> None:
        self._tone_until = time.monotonic() + max(0.1, min(seconds, 2.0))

    async def recv(self) -> AudioFrame:
        loop = asyncio.get_running_loop()
        if self._next_at is None:
            self._next_at = loop.time()
        else:
            self._next_at += FRAME_SAMPLES / SAMPLE_RATE
            await asyncio.sleep(max(0.0, self._next_at - loop.time()))

        raw = self._source.read(FRAME_SAMPLES * PCM_BYTES_PER_FRAME)
        samples = np.frombuffer(raw, dtype="<i2").astype(np.int32).reshape(FRAME_SAMPLES, 2)
        if time.monotonic() < self._tone_until:
            positions = (np.arange(FRAME_SAMPLES) + self._pts) / SAMPLE_RATE
            tone = (np.sin(2 * math.pi * 440 * positions) * 4096).astype(np.int32)
            samples += tone[:, np.newaxis]
        packed = np.clip(samples, -32768, 32767).astype("<i2", copy=False).tobytes()
        frame = AudioFrame(format="s16", layout="stereo", samples=FRAME_SAMPLES)
        frame.planes[0].update(packed)
        frame.sample_rate = SAMPLE_RATE
        frame.pts = self._pts
        frame.time_base = Fraction(1, SAMPLE_RATE)
        self._pts += FRAME_SAMPLES
        return frame

    def stop(self) -> None:
        if self._owns_source:
            self._source.close()
        super().stop()


class TestToneTrack(MediaStreamTrack):
    """Silent outgoing audio with an explicit short audible transport test."""

    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self._pts = 0
        self._next_at: float | None = None
        self._tone_until = 0.0

    def trigger(self, seconds: float = 1.0) -> None:
        self._tone_until = time.monotonic() + max(0.1, min(seconds, 2.0))

    async def recv(self) -> AudioFrame:
        loop = asyncio.get_running_loop()
        if self._next_at is None:
            self._next_at = loop.time()
        else:
            self._next_at += FRAME_SAMPLES / SAMPLE_RATE
            await asyncio.sleep(max(0.0, self._next_at - loop.time()))

        samples = np.zeros((1, FRAME_SAMPLES), dtype=np.int16)
        if time.monotonic() < self._tone_until:
            positions = (np.arange(FRAME_SAMPLES) + self._pts) / SAMPLE_RATE
            samples[0] = (np.sin(2 * math.pi * 440 * positions) * 4096).astype(np.int16)
        frame = AudioFrame.from_ndarray(samples, format="s16", layout="mono")
        frame.sample_rate = SAMPLE_RATE
        frame.pts = self._pts
        frame.time_base = Fraction(1, SAMPLE_RATE)
        self._pts += FRAME_SAMPLES
        return frame


class BrowserCallServer:
    def __init__(
        self,
        sink_factory=CableAudioSink,
        outgoing_factory=CodexProcessAudioTrack,
        source_factory=ProcessLoopbackSource,
    ) -> None:
        self._sink_factory = sink_factory
        self._outgoing_factory = outgoing_factory
        self._source_factory = source_factory
        self._pc: RTCPeerConnection | None = None
        self._sink: CableAudioSink | None = None
        self._outgoing: CodexProcessAudioTrack | None = None
        self._capture: ProcessLoopbackSource | None = None
        self._tasks: set[asyncio.Task] = set()
        self._leave_lock: asyncio.Lock | None = None

    @property
    def active(self) -> bool:
        return self._pc is not None

    def diagnostics(self) -> dict[str, str]:
        pc = self._pc
        sink = self._sink
        peer = classify_peer_state(None if pc is None else getattr(pc, "connectionState", None))
        has_peer = pc is not None
        peak = 0.0
        failed = False
        forwarding = False
        if sink is not None:
            peak = float(getattr(sink, "last_peak", 0.0) or 0.0)
            failed = bool(getattr(sink, "failed", False))
            forwarding = bool(getattr(sink, "is_open", False)) or int(
                getattr(sink, "frames_forwarded", 0) or 0
            ) > 0
        return {
            "peer": peer,
            "browser_audio": classify_browser_audio(has_peer, peak),
            "cable": classify_cable(failed=failed, forwarding=forwarding),
        }

    async def offer(self, request: web.Request) -> web.Response:
        if request.content_length is not None and request.content_length > MAX_OFFER_BYTES:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_OFFER_BYTES, actual_size=request.content_length
            )
        if self.active:
            raise web.HTTPConflict(text="call already active")
        try:
            payload = await request.json()
            sdp = payload["sdp"]
            description_type = payload["type"]
            if not isinstance(sdp, str) or not isinstance(description_type, str):
                raise TypeError
            if len(sdp.encode("utf-8")) > MAX_OFFER_BYTES or description_type != "offer":
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise web.HTTPBadRequest(text="invalid offer") from None

        pc = RTCPeerConnection()
        sink = self._sink_factory()
        started_capture = False
        if self._capture is None:
            try:
                self._capture = self._source_factory()
                self._capture.start()
                started_capture = True
            except Exception:
                self._capture = None
                await pc.close()
                raise web.HTTPConflict(text="Codex audio is unavailable") from None
        try:
            outgoing = self._outgoing_factory(self._capture)
        except Exception:
            if started_capture and self._capture is not None:
                self._capture.close()
                self._capture = None
            await pc.close()
            raise web.HTTPConflict(text="Codex audio is unavailable") from None
        self._pc, self._sink, self._outgoing = pc, sink, outgoing
        pc.addTrack(outgoing)

        @pc.on("track")
        def on_track(track: MediaStreamTrack) -> None:
            if track.kind != "audio":
                return
            task = asyncio.create_task(sink.consume(track))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange() -> None:
            if pc.connectionState in ("failed", "closed"):
                await self.leave()

        try:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=description_type))
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            return web.json_response(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            )
        except Exception:
            await self.leave()
            raise web.HTTPBadRequest(text="negotiation failed") from None

    async def test_tone(self, _request: web.Request) -> web.Response:
        if self._outgoing is None:
            raise web.HTTPConflict(text="no active call")
        self._outgoing.trigger()
        return web.json_response({"ok": True})

    async def end(self, _request: web.Request) -> web.Response:
        await self.leave()
        return web.json_response({"ok": True})

    async def leave(self) -> None:
        if self._leave_lock is None:
            self._leave_lock = asyncio.Lock()
        async with self._leave_lock:
            pc, self._pc = self._pc, None
            outgoing, self._outgoing = self._outgoing, None
            sink, self._sink = self._sink, None
            tasks, self._tasks = tuple(self._tasks), set()
            if sink is not None:
                sink.close()
            if outgoing is not None:
                outgoing.stop()
            for task in tasks:
                task.cancel()
            if tasks:
                _done, pending = await asyncio.wait(tasks, timeout=2)
                for task in pending:
                    task.cancel()
            if pc is not None and pc.connectionState != "closed":
                await pc.close()

    async def close(self) -> None:
        await self.leave()
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.close()


@web.middleware
async def security_headers(request: web.Request, handler):
    response = await handler(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; media-src 'self' blob:; img-src 'self'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["Permissions-Policy"] = "microphone=(self), camera=()"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def build_app(server: BrowserCallServer | None = None) -> web.Application:
    server = server or BrowserCallServer()
    app = web.Application(middlewares=[security_headers], client_max_size=MAX_OFFER_BYTES)

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "index.html")

    async def javascript(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "app.js")

    async def stylesheet(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "styles.css")

    app.router.add_get("/", index)
    app.router.add_get("/app.js", javascript)
    app.router.add_get("/styles.css", stylesheet)
    app.router.add_post("/offer", server.offer)
    app.router.add_post("/test-tone", server.test_tone)
    app.router.add_post("/end", server.end)

    async def diagnostics(_request: web.Request) -> web.Response:
        snapshot = server.diagnostics()
        return web.json_response(
            {
                "peer": snapshot["peer"] if snapshot["peer"] in PEER_STATES else "none",
                "browser_audio": (
                    snapshot["browser_audio"]
                    if snapshot["browser_audio"] in BROWSER_AUDIO_STATES
                    else "no-peer"
                ),
                "cable": snapshot["cable"] if snapshot["cable"] in CABLE_STATES else "inactive",
            }
        )

    app.router.add_get("/diagnostics", diagnostics)

    async def cleanup(_app: web.Application) -> None:
        await server.close()

    app.on_cleanup.append(cleanup)
    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Hermes Voice browser-call spike")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cert")
    parser.add_argument("--key")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loopback = args.host in ("127.0.0.1", "::1", "localhost")
    if not loopback and not (args.cert and args.key):
        raise SystemExit("Non-loopback serving requires --cert and --key.")
    ssl_context = None
    if args.cert or args.key:
        if not (args.cert and args.key):
            raise SystemExit("Both --cert and --key are required.")
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(args.cert, args.key)
    web.run_app(build_app(), host=args.host, port=args.port, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
