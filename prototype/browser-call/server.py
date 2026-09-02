"""One-peer WebRTC bridge between a browser and Codex Voice.

This prototype keeps SDP and audio in memory, serves no diagnostics containing
addresses, and defaults to loopback-only HTTP. Non-loopback serving requires TLS.
Browser audio goes to VB-CABLE. Return audio is captured from the unique
current-session Codex process tree, never from system-wide loopback.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import ctypes
import math
import os
import ssl
import struct
import subprocess
import threading
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
HELPER_SOURCE = STATIC_DIR.parent.parent / "process-loopback" / "ProcessLoopbackCapture.cs"
HELPER_BUILD_SCRIPT = STATIC_DIR.parent.parent / "process-loopback" / "build-helper.ps1"
HELPER_EXE = STATIC_DIR.parent / "build" / "ProcessLoopbackCapture.exe"
PCM_BYTES_PER_FRAME = 4
PCM_BUFFER_LIMIT = SAMPLE_RATE * PCM_BYTES_PER_FRAME * 2


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


def pick_unique_codex_process(rows: list[dict[str, Any]], session_id: int) -> int:
    matches = [
        int(row["pid"])
        for row in rows
        if row.get("visible") is True
        and row.get("owner") is False
        and str(row.get("class_name", "")).startswith("Chrome_WidgetWin")
        and str(row.get("process_name", "")).lower() == "chatgpt.exe"
        and int(row.get("session_id", -1)) == session_id
        and int(row.get("pid", 0)) > 0
    ]
    if len(matches) != 1:
        raise RuntimeError("exactly one current-session Codex main window is required")
    return matches[0]


def find_unique_codex_process() -> int:
    if os.name != "nt":
        raise RuntimeError("Codex process capture requires Windows")
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    session_id = wintypes.DWORD()
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD
    kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
    if not kernel32.ProcessIdToSessionId(kernel32.GetCurrentProcessId(), ctypes.byref(session_id)):
        raise RuntimeError("current Windows session is unavailable")

    rows: list[dict[str, Any]] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, 4):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_session = wintypes.DWORD()
        if not kernel32.ProcessIdToSessionId(pid.value, ctypes.byref(process_session)):
            return True
        name_buffer = ctypes.create_unicode_buffer(260)
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        process_name = ""
        if handle:
            try:
                size = wintypes.DWORD(len(name_buffer))
                kernel32.QueryFullProcessImageNameW(handle, 0, name_buffer, ctypes.byref(size))
                process_name = Path(name_buffer.value).name
            finally:
                kernel32.CloseHandle(handle)
        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buffer, 256)
        rows.append(
            {
                "visible": True,
                "owner": bool(user32.GetWindow(hwnd, 4)),
                "class_name": class_buffer.value,
                "process_name": process_name,
                "session_id": int(process_session.value),
                "pid": int(pid.value),
            }
        )
        return True

    callback_ref = EnumWindowsProc(callback)
    if not user32.EnumWindows(callback_ref, 0):
        raise RuntimeError("Codex window discovery failed")
    return pick_unique_codex_process(rows, int(session_id.value))


def ensure_process_loopback_helper() -> Path:
    if os.name != "nt":
        raise RuntimeError("Codex process capture requires Windows")
    if not HELPER_SOURCE.is_file() or not HELPER_BUILD_SCRIPT.is_file():
        raise RuntimeError("process-loopback helper source is missing")
    if HELPER_EXE.is_file() and HELPER_EXE.stat().st_mtime >= HELPER_SOURCE.stat().st_mtime:
        return HELPER_EXE
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(HELPER_BUILD_SCRIPT),
            "-OutputPath",
            str(HELPER_EXE),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0 or not HELPER_EXE.is_file():
        raise RuntimeError("process-loopback helper build failed")
    return HELPER_EXE


class ProcessLoopbackSource:
    """Own one native Codex process-tree capture child and a bounded PCM queue."""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._closed = False
        self._failed = False

    def start(self) -> None:
        if self._process is not None:
            return
        helper = ensure_process_loopback_helper()
        pid = find_unique_codex_process()
        process = subprocess.Popen(
            [str(helper), "--pid", str(pid), "--raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._process = process
        assert process.stdout is not None
        header = process.stdout.read(12)
        if len(header) != 12 or header[:4] != b"HVPC":
            self.close()
            raise RuntimeError("Codex process-loopback activation failed")
        sample_rate, channels, bits = struct.unpack("<IHH", header[4:])
        if (sample_rate, channels, bits) != (SAMPLE_RATE, 2, 16):
            self.close()
            raise RuntimeError("Codex process-loopback format is unsupported")
        self._reader = threading.Thread(
            target=self._read_loop,
            name="hermes-voice-process-loopback",
            daemon=True,
        )
        self._reader.start()

    def _read_loop(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            while not self._closed:
                chunk = process.stdout.read(16384)
                if not chunk:
                    break
                with self._lock:
                    self._buffer.extend(chunk)
                    if len(self._buffer) > PCM_BUFFER_LIMIT:
                        overflow = len(self._buffer) - PCM_BUFFER_LIMIT
                        del self._buffer[: overflow - (overflow % PCM_BYTES_PER_FRAME)]
        finally:
            if not self._closed:
                self._failed = True

    def read(self, byte_count: int) -> bytes:
        if self._failed:
            raise RuntimeError("Codex process-loopback child stopped")
        with self._lock:
            take = min(byte_count, len(self._buffer))
            take -= take % PCM_BYTES_PER_FRAME
            result = bytes(self._buffer[:take])
            del self._buffer[:take]
        if len(result) < byte_count:
            result += bytes(byte_count - len(result))
        return result

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        process = self._process
        self._process = None
        if process is not None:
            if process.poll() is None and process.stdin is not None:
                with contextlib.suppress(OSError):
                    process.stdin.write(b"\n")
                    process.stdin.flush()
                    process.stdin.close()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
            for pipe in (process.stdout, process.stderr):
                if pipe is not None:
                    with contextlib.suppress(OSError):
                        pipe.close()
        reader, self._reader = self._reader, None
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=1)
        with self._lock:
            self._buffer.clear()


class CodexProcessAudioTrack(MediaStreamTrack):
    """Timed 48 kHz Codex-only PCM, plus an explicit short test tone."""

    kind = "audio"

    def __init__(self, source_factory=ProcessLoopbackSource) -> None:
        super().__init__()
        self._source = source_factory()
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
    def __init__(self, sink_factory=CableAudioSink, outgoing_factory=CodexProcessAudioTrack) -> None:
        self._sink_factory = sink_factory
        self._outgoing_factory = outgoing_factory
        self._pc: RTCPeerConnection | None = None
        self._sink: CableAudioSink | None = None
        self._outgoing: CodexProcessAudioTrack | None = None
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
        try:
            outgoing = self._outgoing_factory()
        except Exception:
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
        if self._outgoing is None:
            raise web.HTTPConflict(text="no active call")
        self._outgoing.trigger()
        return web.json_response({"ok": True})

    async def end(self, _request: web.Request) -> web.Response:
        await self.close()
        return web.json_response({"ok": True})

    async def close(self) -> None:
        pc, self._pc = self._pc, None
        outgoing, self._outgoing = self._outgoing, None
        tasks, self._tasks = tuple(self._tasks), set()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if self._sink is not None:
            self._sink.close()
            self._sink = None
        if outgoing is not None:
            outgoing.stop()
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
