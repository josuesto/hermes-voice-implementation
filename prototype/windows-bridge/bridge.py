"""Local Windows audio spike for Codex Voice.

Lists capture and playback endpoints, plays a short 440 Hz test tone,
monitors system-output loopback, and can forward a selected physical
microphone into VB-CABLE. Audio bytes are never written to disk. This
spike does not change Windows default devices.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

SESSION_NAME = "hermes-voice-windows-bridge-session.json"
TONE_HZ = 440.0
TONE_AMPLITUDE = 0.2
DEFAULT_SECONDS = 0.8
SAMPLE_RATE = 48000
INJECTION_CLASSES = frozenset({"vb-cable", "voicemeeter", "virtual-other"})
STOP_WAIT_SECONDS = 2.0
CABLE_INPUT_NAME = "CABLE Input (VB-Audio Virtual Cable)"

_SNAPSHOT: dict[str, Any] | None = None
_MONITOR_ACTIVE = False


def session_path() -> Path:
    return Path(tempfile.gettempdir()) / SESSION_NAME


def stop_path() -> Path:
    return session_path().with_suffix(".stop")


def classify_name(name: str, is_loopback: bool = False) -> str:
    n = (name or "").lower()
    if any(token in n for token in ("vb-audio", "vb-cable", "cable input", "cable output")):
        return "vb-cable"
    if "voicemeeter" in n:
        return "voicemeeter"
    if "virtual" in n:
        return "virtual-other"
    if any(token in n for token in ("stereo mix", "what u hear", "wave out mix")):
        return "stereo-mix"
    if is_loopback or "loopback" in n:
        return "loopback"
    return "physical-or-other"


def id_token(*parts: object) -> str:
    raw = "|".join(str(p) for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def _query_devices() -> list[dict[str, Any]]:
    import soundcard as sc

    rows: list[dict[str, Any]] = []
    default_spk = sc.default_speaker()
    default_mic = sc.default_microphone()
    speakers = list(sc.all_speakers())
    mics = list(sc.all_microphones(include_loopback=True))
    for index, device in enumerate(speakers):
        name = str(device.name)
        ident = str(getattr(device, "id", name))
        rows.append(
            {
                "index": index,
                "kind": "playback",
                "class": classify_name(name, is_loopback=False),
                "default": ident == str(getattr(default_spk, "id", default_spk.name)),
                "hostapi": "wasapi",
                "name": name,
                "id_token": id_token("playback", ident),
                "_ident": ident,
            }
        )
    for index, device in enumerate(mics):
        name = str(device.name)
        ident = str(getattr(device, "id", name))
        is_loopback = bool(getattr(device, "isloopback", False))
        rows.append(
            {
                "index": index,
                "kind": "capture",
                "class": classify_name(name, is_loopback=is_loopback),
                "default": (not is_loopback)
                and ident == str(getattr(default_mic, "id", default_mic.name)),
                "hostapi": "wasapi",
                "name": name,
                "id_token": id_token("capture", ident, is_loopback),
                "_ident": ident,
                "_loopback": is_loopback,
            }
        )
    return rows


def sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": row["index"],
        "kind": row["kind"],
        "class": row["class"],
        "default": row["default"],
        "hostapi": row["hostapi"],
        "id_token": row["id_token"],
    }


def class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return counts


def has_programmable_mic(rows: list[dict[str, Any]]) -> bool:
    return any(
        row["kind"] == "capture"
        and row["class"] in INJECTION_CLASSES
        and not row.get("_loopback")
        for row in rows
    )


def generate_tone(seconds: float, samplerate: int = SAMPLE_RATE) -> Any:
    import numpy as np

    n = max(1, int(samplerate * seconds))
    t = np.arange(n, dtype=np.float32) / float(samplerate)
    return (TONE_AMPLITUDE * np.sin(2.0 * np.pi * np.float32(TONE_HZ) * t)).astype(np.float32)


def _codex_desktop_present() -> bool:
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    names = {"chatgpt.exe", "codex.exe", "codex-code-mode-host.exe"}
    TH32CS_SNAPPROCESS = 0x2

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == -1:
        return False
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return False
        while True:
            if entry.szExeFile.lower() in names:
                return True
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return False
    finally:
        kernel32.CloseHandle(snapshot)


def _write_session(payload: dict[str, Any]) -> None:
    session_path().write_text(json.dumps(payload), encoding="utf-8")


def _read_session() -> dict[str, Any] | None:
    path = session_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _request_stop() -> None:
    stop_path().write_text("stop", encoding="utf-8")


def _clear_stop() -> None:
    path = stop_path()
    if path.exists():
        path.unlink()


def _stop_requested() -> bool:
    return stop_path().is_file()


def session_running() -> bool:
    return _MONITOR_ACTIVE and not _stop_requested()


def _default_speaker_and_loopback() -> tuple[Any, Any]:
    import soundcard as sc

    speaker = sc.default_speaker()
    loopbacks = [
        mic
        for mic in sc.all_microphones(include_loopback=True)
        if mic.isloopback and mic.name == speaker.name
    ]
    if not loopbacks:
        raise RuntimeError("No WASAPI loopback microphone matches the default playback device.")
    return speaker, loopbacks[0]


def _play_tone(seconds: float, device_index: int | None = None) -> None:
    import numpy as np
    import soundcard as sc

    if device_index is None:
        speaker = sc.default_speaker()
    else:
        speakers = list(sc.all_speakers())
        if device_index < 0 or device_index >= len(speakers):
            raise RuntimeError("Playback device index is out of range.")
        speaker = speakers[device_index]
    channels = max(1, min(2, int(speaker.channels)))
    tone = generate_tone(seconds, samplerate=SAMPLE_RATE)
    play = np.column_stack([tone] * channels) if channels > 1 else tone
    with speaker.player(samplerate=SAMPLE_RATE, channels=channels) as player:
        player.play(play)


def _route_devices(source_index: int) -> tuple[Any, Any]:
    import soundcard as sc

    microphones = list(sc.all_microphones(include_loopback=True))
    if source_index < 0 or source_index >= len(microphones):
        raise RuntimeError("Capture device index is out of range.")
    source = microphones[source_index]
    source_class = classify_name(str(source.name), bool(source.isloopback))
    if bool(source.isloopback) or source_class != "physical-or-other":
        raise RuntimeError("Source must be a physical microphone, not loopback or virtual cable.")
    sinks = [speaker for speaker in sc.all_speakers() if str(speaker.name) == CABLE_INPUT_NAME]
    if len(sinks) != 1:
        raise RuntimeError("Exactly one standard VB-CABLE Input playback endpoint is required.")
    return source, sinks[0]


def pick_wasapi_device_index(
    devices: Any,
    hostapis: Any,
    *,
    name: str,
    direction: str,
) -> int:
    """Resolve one exact PortAudio WASAPI device for input or output."""
    channel_key = "max_input_channels" if direction == "input" else "max_output_channels"
    matches = []
    for index, device in enumerate(devices):
        hostapi = hostapis[int(device["hostapi"])]
        if (
            str(hostapi["name"]) == "Windows WASAPI"
            and str(device["name"]) == name
            and int(device[channel_key]) > 0
        ):
            matches.append(index)
    if len(matches) != 1:
        raise RuntimeError(f"Exactly one WASAPI {direction} device named {name!r} is required.")
    return matches[0]


def _adapt_channels(chunk: Any, output_channels: int) -> Any:
    import numpy as np

    audio = np.asarray(chunk, dtype=np.float32)
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]
    if audio.ndim != 2 or audio.shape[1] < 1:
        raise RuntimeError("Microphone returned an unsupported audio shape.")
    if output_channels == audio.shape[1]:
        return audio
    if output_channels == 1:
        return np.mean(audio, axis=1, keepdims=True, dtype=np.float32)
    if audio.shape[1] == 1:
        return np.repeat(audio, output_channels, axis=1)
    if audio.shape[1] > output_channels:
        return audio[:, :output_channels]
    repeats = (output_channels + audio.shape[1] - 1) // audio.shape[1]
    return np.tile(audio, (1, repeats))[:, :output_channels]


def cmd_route_mic(source: int, seconds: float) -> int:
    """Forward one physical capture endpoint to standard VB-CABLE in memory."""
    global _MONITOR_ACTIVE

    import numpy as np
    import sounddevice as sd

    if seconds <= 0:
        print("running=false error=seconds_required")
        return 2
    microphone, cable_input = _route_devices(source)
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    input_index = pick_wasapi_device_index(
        devices, hostapis, name=str(microphone.name), direction="input"
    )
    output_index = pick_wasapi_device_index(
        devices, hostapis, name=str(cable_input.name), direction="output"
    )
    input_channels = max(1, min(2, int(devices[input_index]["max_input_channels"])))
    output_channels = max(1, min(2, int(devices[output_index]["max_output_channels"])))
    deadline = time.monotonic() + seconds
    metrics = {"frames": 0, "peak": 0.0, "status_events": 0}

    def _callback(indata, outdata, frame_count, _time_info, status) -> None:
        if status:
            metrics["status_events"] += 1
        metrics["peak"] = max(metrics["peak"], float(np.max(np.abs(indata))))
        metrics["frames"] += int(frame_count)
        outdata[:] = _adapt_channels(indata, output_channels)

    _clear_stop()
    _MONITOR_ACTIVE = True
    print("running=true route=physical-mic-to-vb-cable saved_audio=false")
    try:
        with sd.Stream(
            device=(input_index, output_index),
            samplerate=SAMPLE_RATE,
            blocksize=int(SAMPLE_RATE * 0.01),
            channels=(input_channels, output_channels),
            dtype="float32",
            latency="low",
            callback=_callback,
        ):
            while time.monotonic() < deadline and not _stop_requested():
                time.sleep(0.05)
    finally:
        _MONITOR_ACTIVE = False
        _write_session(
            {
                "running": False,
                "peak_rms_proxy": round(metrics["peak"], 6),
                "frames_seen": metrics["frames"],
                "frames_discarded": metrics["frames"],
                "saved_audio": False,
            }
        )
    print(
        f"running=false route=physical-mic-to-vb-cable "
        f"peak_rms_proxy={round(metrics['peak'], 6)} "
        f"frames_forwarded={metrics['frames']} status_events={metrics['status_events']} "
        "saved_audio=false"
    )
    return 0


def cmd_list(sanitize: bool) -> int:
    rows = _query_devices()
    printable = [sanitize_row(row) if sanitize else {k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
    for row in printable:
        line = (
            f"index={row['index']} kind={row['kind']} class={row['class']} "
            f"default={str(row['default']).lower()} hostapi={row['hostapi']} "
            f"id_token={row['id_token']}"
        )
        if not sanitize:
            line += f" name={row['name']}"
        print(line)
    print(f"count={len(rows)}")
    print(f"programmable_mic={str(has_programmable_mic(rows)).lower()}")
    return 0


def cmd_play(device: int | None, seconds: float) -> int:
    _play_tone(seconds, device_index=device)
    print(f"played_hz={int(TONE_HZ)} seconds={seconds} saved_audio=false")
    return 0


def cmd_start(seconds: float | None = None) -> int:
    if not seconds or seconds <= 0:
        print("running=false error=seconds_required")
        return 2
    if session_running():
        print("running=true already=true")
        return 1
    _clear_stop()
    return cmd_run_monitor(max_seconds=seconds)


def cmd_stop() -> int:
    _request_stop()
    if not _MONITOR_ACTIVE:
        print("running=false")
        return 0
    deadline = time.monotonic() + STOP_WAIT_SECONDS
    while time.monotonic() < deadline:
        if not _MONITOR_ACTIVE:
            print("running=false")
            return 0
        time.sleep(0.05)
    print("running=true stop_failed=true reason=cooperative_stop_timeout")
    return 1


def cmd_run_monitor(max_seconds: float) -> int:
    global _MONITOR_ACTIVE

    import numpy as np

    speaker, loopback = _default_speaker_and_loopback()
    del speaker
    peak = 0.0
    frames = 0
    t0 = time.monotonic()
    _MONITOR_ACTIVE = True
    _write_session(
        {
            "running": True,
            "peak_rms_proxy": 0.0,
            "frames_seen": 0,
            "frames_discarded": 0,
            "saved_audio": False,
        }
    )
    print("running=true")
    channels = max(1, min(2, int(loopback.channels)))
    try:
        with loopback.recorder(samplerate=SAMPLE_RATE, channels=channels) as recorder:
            while not _stop_requested():
                if (time.monotonic() - t0) >= max_seconds:
                    break
                chunk = recorder.record(numframes=int(SAMPLE_RATE * 0.2))
                peak = max(peak, float(np.max(np.abs(chunk))))
                frames += int(chunk.shape[0])
                del chunk
                if _stop_requested():
                    break
                _write_session(
                    {
                        "running": True,
                        "peak_rms_proxy": round(peak, 6),
                        "frames_seen": frames,
                        "frames_discarded": frames,
                        "saved_audio": False,
                    }
                )
    finally:
        _MONITOR_ACTIVE = False
        _write_session(
            {
                "running": False,
                "peak_rms_proxy": round(peak, 6),
                "frames_seen": frames,
                "frames_discarded": frames,
                "saved_audio": False,
            }
        )
    print(
        f"running=false peak_rms_proxy={round(peak, 6)} frames_discarded={frames} saved_audio=false"
    )
    return 0


def cmd_spike(seconds: float) -> int:
    import numpy as np

    speaker, loopback = _default_speaker_and_loopback()
    play_channels = max(1, min(2, int(speaker.channels)))
    rec_channels = max(1, min(2, int(loopback.channels)))
    tone = generate_tone(seconds, samplerate=SAMPLE_RATE)
    play = np.column_stack([tone] * play_channels) if play_channels > 1 else tone
    captured = {"peak": 0.0, "frames": 0}

    def _play() -> None:
        with speaker.player(samplerate=SAMPLE_RATE, channels=play_channels) as player:
            player.play(play)

    worker = threading.Thread(target=_play, daemon=True)
    with loopback.recorder(samplerate=SAMPLE_RATE, channels=rec_channels) as recorder:
        worker.start()
        chunk = recorder.record(numframes=int(SAMPLE_RATE * (seconds + 0.3)))
        captured["peak"] = float(np.max(np.abs(chunk)))
        captured["frames"] = int(chunk.shape[0])
        del chunk
        worker.join(timeout=seconds + 2.0)
    print(
        f"peak_rms_proxy={round(captured['peak'], 6)} frames_seen={captured['frames']} "
        f"frames_discarded={captured['frames']} saved_audio=false "
        f"programmable_mic={str(has_programmable_mic(_query_devices())).lower()}"
    )
    return 0


def cmd_status() -> int:
    running = session_running()
    print(f"running={str(running).lower()}")
    print(f"codex_desktop_present={str(_codex_desktop_present()).lower()}")
    rows = _query_devices()
    session = _read_session() or {}
    counts = class_counts(rows)
    programmable = has_programmable_mic(rows)
    print(f"programmable_mic={str(programmable).lower()}")
    print(f"endpoint_rows={len(rows)}")
    print("saved_audio=false")
    print("default_devices_changed=false")
    for key in sorted(counts):
        print(f"class.{key}={counts[key]}")
    if session:
        print(f"last_peak_rms_proxy={session.get('peak_rms_proxy', 0)}")
        print(f"frames_discarded={session.get('frames_discarded', 0)}")
    if not programmable:
        print("blocker=missing_virtual_cable")
        print("candidate=vb-cable")
    return 0


def cmd_restore() -> int:
    global _SNAPSHOT
    _SNAPSHOT = None
    print("changed=false restored=false reason=no_defaults_modified")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Windows audio spike for Codex Voice.")
    sub = parser.add_subparsers(dest="command", required=True)
    list_p = sub.add_parser("list", help="List capture and playback endpoints.")
    list_p.add_argument("--sanitize", action="store_true", help="Omit endpoint names.")
    play_p = sub.add_parser("play", help="Play a short 440 Hz test tone.")
    play_p.add_argument("--device", type=int, default=None)
    play_p.add_argument("--seconds", type=float, default=DEFAULT_SECONDS)
    start_p = sub.add_parser("start", help="Start a bounded in-process WASAPI loopback monitor.")
    start_p.add_argument("--seconds", type=float, required=True, help="Run in-process then stop.")
    sub.add_parser("stop", help="Request a cooperative stop of the in-process monitor.")
    sub.add_parser("status", help="Print sanitized bridge and endpoint status.")
    sub.add_parser("restore", help="Restore defaults this process changed.")
    spike_p = sub.add_parser("spike", help="Play a test tone while monitoring loopback.")
    spike_p.add_argument("--seconds", type=float, default=DEFAULT_SECONDS)
    route_p = sub.add_parser(
        "route-mic", help="Forward one physical capture device to standard VB-CABLE Input."
    )
    route_p.add_argument("--source", type=int, required=True, help="Capture index from list output.")
    route_p.add_argument("--seconds", type=float, required=True, help="Bounded run duration.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    command = args.command
    if command == "list":
        return cmd_list(sanitize=bool(args.sanitize))
    if command == "play":
        return cmd_play(device=args.device, seconds=float(args.seconds))
    if command == "start":
        return cmd_start(seconds=args.seconds)
    if command == "stop":
        return cmd_stop()
    if command == "status":
        return cmd_status()
    if command == "restore":
        return cmd_restore()
    if command == "spike":
        return cmd_spike(seconds=float(args.seconds))
    if command == "route-mic":
        return cmd_route_mic(source=int(args.source), seconds=float(args.seconds))
    raise SystemExit(f"unknown command {command}")


if __name__ == "__main__":
    raise SystemExit(main())
