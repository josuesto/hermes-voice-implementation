"""One-peer WebRTC spike for browser microphone audio into VB-CABLE.

This prototype keeps SDP and audio in memory, serves no diagnostics containing
addresses, and defaults to loopback-only HTTP. Non-loopback serving requires TLS.
The return track is silence except for an explicit one-second transport test tone;
Codex-only process capture replaces it in the next MVP-03 slice.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import ctypes
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

CABLE_INPUT_NAME = "CABLE Input (VB-Audio Virtual Cable)"
SAMPLE_RATE = 48000
FRAME_SAMPLES = 960
MAX_OFFER_BYTES = 131072
STATIC_DIR = Path(__file__).resolve().parent / "static"


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


class CableAudioSink:
    """Consume one browser track and write float PCM to CABLE Input."""

    def __init__(self) -> None:
        self._stream = None
        self._coinitialized = False
        self.frames_forwarded = 0

    def open(self) -> None:
        if self._stream is not None:
            return
        import sounddevice as sd

        if os.name == "nt":
            result = int(ctypes.windll.ole32.CoInitializeEx(None, 0))
            if result not in (0, 1, -2147417850):
                raise OSError("COM initialization failed")
            self._coinitialized = result in (0, 1)

        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            device = pick_wasapi_output(devices, hostapis)
            channels = max(1, min(2, int(devices[device]["max_output_channels"])))
            self._stream = sd.OutputStream(
                device=device,
                samplerate=SAMPLE_RATE,
                blocksize=FRAME_SAMPLES,
                channels=channels,
                dtype="float32",
                latency="low",
            )
            self._stream.start()
        except Exception:
            if self._coinitialized:
                ctypes.windll.ole32.CoUninitialize()
                self._coinitialized = False
            raise

    async def consume(self, track: MediaStreamTrack) -> None:
        self.open()
        resampler = AudioResampler(format="fltp", layout="stereo", rate=SAMPLE_RATE)
        try:
            while True:
                frame = await track.recv()
                for converted in resampler.resample(frame):
                    audio = converted.to_ndarray().astype(np.float32, copy=False)
                    if audio.ndim != 2:
                        raise RuntimeError("unsupported browser audio shape")
                    packed = np.ascontiguousarray(audio.T)
                    self._stream.write(packed)
                    self.frames_forwarded += int(packed.shape[0])
        except (MediaStreamError, asyncio.CancelledError):
            raise
        finally:
            self.close()

    def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            with contextlib.suppress(Exception):
                stream.stop()
            with contextlib.suppress(Exception):
                stream.close()
        if self._coinitialized:
            ctypes.windll.ole32.CoUninitialize()
            self._coinitialized = False


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
    def __init__(self, sink_factory=CableAudioSink) -> None:
        self._sink_factory = sink_factory
        self._pc: RTCPeerConnection | None = None
        self._sink: CableAudioSink | None = None
        self._tone: TestToneTrack | None = None
        self._tasks: set[asyncio.Task] = set()

    @property
    def active(self) -> bool:
        return self._pc is not None

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
        tone = TestToneTrack()
        self._pc, self._sink, self._tone = pc, sink, tone
        pc.addTrack(tone)

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
                await self.close()

        try:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=description_type))
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            return web.json_response(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            )
        except Exception:
            await self.close()
            raise web.HTTPBadRequest(text="negotiation failed") from None

    async def test_tone(self, _request: web.Request) -> web.Response:
        if self._tone is None:
            raise web.HTTPConflict(text="no active call")
        self._tone.trigger()
        return web.json_response({"ok": True})

    async def end(self, _request: web.Request) -> web.Response:
        await self.close()
        return web.json_response({"ok": True})

    async def close(self) -> None:
        pc, self._pc = self._pc, None
        self._tone = None
        tasks, self._tasks = tuple(self._tasks), set()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._sink is not None:
            self._sink.close()
            self._sink = None
        if pc is not None and pc.connectionState != "closed":
            await pc.close()


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
