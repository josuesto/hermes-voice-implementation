"""Transport-neutral VB-CABLE sink and Codex-only process-loopback capture.

Browser WebRTC and Discord both reuse these primitives. This module does not
import aiohttp, aiortc, or av. A 20 ms stereo s16le packet is 3,840 bytes.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import struct
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

CABLE_INPUT_NAME = "CABLE Input (VB-Audio Virtual Cable)"
SAMPLE_RATE = 48000
FRAME_SAMPLES = 960
_COMPANION_DIR = Path(__file__).resolve().parent
HELPER_SOURCE = _COMPANION_DIR / "process_loopback" / "ProcessLoopbackCapture.cs"
HELPER_BUILD_SCRIPT = _COMPANION_DIR / "process_loopback" / "build-helper.ps1"
HELPER_EXE = _COMPANION_DIR / "process_loopback" / "build" / "ProcessLoopbackCapture.exe"
PCM_BYTES_PER_FRAME = 4
PCM_PACKET_BYTES = FRAME_SAMPLES * PCM_BYTES_PER_FRAME
PCM_BUFFER_LIMIT = SAMPLE_RATE * PCM_BYTES_PER_FRAME * 2
FRAME_INTERVAL_S = FRAME_SAMPLES / SAMPLE_RATE


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
    """Write float or s16le PCM to CABLE Input."""

    def __init__(self) -> None:
        self._stream = None
        self._coinitialized = False
        self.frames_forwarded = 0
        self.last_peak = 0.0
        self.last_write_at: float | None = None
        self.failed = False

    @property
    def is_open(self) -> bool:
        return self._stream is not None

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

    def write_float(self, packed: np.ndarray) -> None:
        stream = self._stream
        if stream is None:
            return
        if packed.ndim != 2:
            raise RuntimeError("unsupported pcm shape")
        channels = int(getattr(stream, "channels", packed.shape[1]))
        if packed.shape[1] == channels:
            data = packed
        elif channels == 1:
            data = packed.mean(axis=1, keepdims=True).astype(np.float32, copy=False)
        else:
            data = packed
        self.last_peak = float(np.max(np.abs(packed))) if packed.size else 0.0
        stream.write(np.ascontiguousarray(data, dtype=np.float32))
        self.frames_forwarded += int(packed.shape[0])
        self.last_write_at = time.monotonic()

    def write_pcm(self, pcm: bytes) -> None:
        if len(pcm) == 0:
            return
        if len(pcm) % PCM_BYTES_PER_FRAME != 0:
            raise ValueError("pcm must be interleaved stereo s16le")
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        packed = np.ascontiguousarray(samples.reshape(-1, 2))
        self.write_float(packed)

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
    HELPER_EXE.parent.mkdir(parents=True, exist_ok=True)
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

    def start(self, header_timeout_s: float = 15.0) -> None:
        if self._process is not None:
            return
        helper = ensure_process_loopback_helper()
        pid = find_unique_codex_process()
        process = subprocess.Popen(
            [str(helper), "--pid", str(pid), "--raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._process = process
        try:
            assert process.stdout is not None
            header = self._read_pipe(process.stdout, 12, header_timeout_s)
            if len(header) != 12 or header[:4] != b"HVPC":
                raise RuntimeError("Codex process-loopback activation failed")
            sample_rate, channels, bits = struct.unpack("<IHH", header[4:])
            if (sample_rate, channels, bits) != (SAMPLE_RATE, 2, 16):
                raise RuntimeError("Codex process-loopback format is unsupported")
            self._reader = threading.Thread(
                target=self._read_loop,
                name="hermes-voice-process-loopback",
                daemon=True,
            )
            self._reader.start()
        except Exception:
            self.close()
            raise

    def _read_pipe(self, pipe, byte_count: int, timeout_s: float) -> bytes:
        collected = bytearray()
        errors: list[BaseException] = []

        def target() -> None:
            try:
                remaining = byte_count
                while remaining > 0:
                    chunk = pipe.read(remaining)
                    if not chunk:
                        break
                    collected.extend(chunk)
                    remaining -= len(chunk)
            except BaseException as exc:
                errors.append(exc)

        worker = threading.Thread(
            target=target, name="hermes-voice-loopback-header", daemon=True
        )
        worker.start()
        worker.join(timeout_s)
        if worker.is_alive():
            raise TimeoutError("Codex process-loopback activation timed out")
        if errors:
            raise errors[0]
        return bytes(collected)

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

    def flush(self) -> None:
        with self._lock:
            self._buffer.clear()

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
            if process.stdout is not None:
                with contextlib.suppress(OSError):
                    process.stdout.close()
        reader, self._reader = self._reader, None
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=1)
        with self._lock:
            self._buffer.clear()
