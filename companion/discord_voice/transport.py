"""Owned Discord voice sidecar: one guild channel, owner-only PCM."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from companion.audio_io import (
    FRAME_INTERVAL_S,
    PCM_PACKET_BYTES,
    CableAudioSink,
    ProcessLoopbackSource,
)
from companion.discord_voice.protocol import (
    TYPE_CONTROL,
    TYPE_PCM_IN,
    TYPE_PCM_OUT,
    ProtocolError,
    decode_control,
    encode_control,
    encode_frame,
    read_frame,
)

TOKEN_ENV = "HERMES_VOICE_DISCORD_TOKEN"
GUILD_ENV = "HERMES_VOICE_DISCORD_GUILD_ID"
CHANNEL_ENV = "HERMES_VOICE_DISCORD_CHANNEL_ID"
OWNER_ENV = "HERMES_VOICE_DISCORD_OWNER_ID"
SECRET_ENVS = (TOKEN_ENV, GUILD_ENV, CHANNEL_ENV, OWNER_ENV)
SIDECAR_DIR = Path(__file__).resolve().parent / "sidecar"
SIDECAR_ENTRY = SIDECAR_DIR / "src" / "index.mjs"
CONNECTION_STATES = frozenset({"idle", "connecting", "connected", "failed"})
AUDIENCE_STATES = frozenset({"waiting_for_owner", "owner_present", "audience_blocked"})
INCOMING_STATES = frozenset({"silent", "receiving", "failed"})
OUTGOING_STATES = frozenset({"silent", "sending", "failed"})
CABLE_STATES = frozenset({"inactive", "forwarding", "failed"})
ACTIVITY_WINDOW_S = 0.5
CONNECT_WAIT_S = 12.0
QUEUE_LIMIT = 3
IDLE_DIAGNOSTICS = {
    "connection": "idle",
    "audience": "waiting_for_owner",
    "incoming": "silent",
    "cable": "inactive",
    "outgoing": "silent",
}


def _snowflake(value: str) -> bool:
    return value.isdigit() and 17 <= len(value) <= 20


@dataclass(frozen=True)
class DiscordConfig:
    token: str
    guild_id: str
    channel_id: str
    owner_id: str

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> DiscordConfig | None:
        source = env if env is not None else os.environ
        token = str(source.get(TOKEN_ENV, "")).strip()
        guild_id = str(source.get(GUILD_ENV, "")).strip()
        channel_id = str(source.get(CHANNEL_ENV, "")).strip()
        owner_id = str(source.get(OWNER_ENV, "")).strip()
        if not token or not _snowflake(guild_id) or not _snowflake(channel_id) or not _snowflake(owner_id):
            return None
        return cls(token=token, guild_id=guild_id, channel_id=channel_id, owner_id=owner_id)


def classify_activity(
    last_at: float | None,
    now: float,
    *,
    failed: bool,
    active: str,
    idle: str,
    window_s: float = ACTIVITY_WINDOW_S,
) -> str:
    if failed:
        return "failed"
    if last_at is not None and (now - last_at) <= window_s:
        return active
    return idle


def child_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(source if source is not None else os.environ)
    for key in SECRET_ENVS:
        env.pop(key, None)
    return env


class DiscordVoiceTransport:
    """Spawn the Node sidecar and bridge owner PCM through VB-CABLE."""

    def __init__(
        self,
        *,
        config: DiscordConfig | None = None,
        env: dict[str, str] | None = None,
        command: list[str] | None = None,
        sink_factory: Callable[[], Any] = CableAudioSink,
        source_factory: Callable[[], Any] = ProcessLoopbackSource,
        connect_wait_s: float = CONNECT_WAIT_S,
        activity_window_s: float = ACTIVITY_WINDOW_S,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._env = env
        self._command = command
        self._sink_factory = sink_factory
        self._source_factory = source_factory
        self._connect_wait_s = connect_wait_s
        self._activity_window_s = activity_window_s
        self._sleep = sleep
        self._monotonic = monotonic
        self._process: subprocess.Popen | None = None
        self._sink: Any | None = None
        self._source: Any | None = None
        self._reader: threading.Thread | None = None
        self._pacer: threading.Thread | None = None
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._closed = threading.Event()
        self._audio_enabled = False
        self._connection = "idle"
        self._audience = "waiting_for_owner"
        self._last_error: str | None = None
        self._last_inbound_at: float | None = None
        self._last_outbound_at: float | None = None
        self._last_cable_at: float | None = None
        self._inbound: deque[bytes] = deque(maxlen=QUEUE_LIMIT)
        self._media_failed = False

    def start(self) -> bool:
        if self.is_running():
            return True
        config = self._config if self._config is not None else DiscordConfig.from_env(self._env)
        if config is None:
            self._last_error = "discord_config_missing"
            return False
        command = self._command or self._default_command()
        if command is None:
            self._last_error = "discord_dependency_missing"
            return False
        self._closed.clear()
        self._audio_enabled = False
        self._media_failed = False
        self._connection = "connecting"
        self._audience = "waiting_for_owner"
        self._last_error = None
        popen_kw: dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "bufsize": 0,
            "env": child_environment(self._env),
        }
        if self._command is None:
            popen_kw["cwd"] = str(SIDECAR_DIR)
            popen_kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._process = subprocess.Popen(command, **popen_kw)
        except OSError:
            self._last_error = "discord_start_failed"
            self._connection = "failed"
            return False
        try:
            self._send_control(
                {
                    "op": "bootstrap",
                    "token": config.token,
                    "guild_id": config.guild_id,
                    "channel_id": config.channel_id,
                    "owner_id": config.owner_id,
                }
            )
        except OSError:
            self._fail("discord_start_failed")
            return False
        self._reader = threading.Thread(target=self._read_loop, name="hermes-discord-pipe", daemon=True)
        self._reader.start()
        deadline = self._monotonic() + self._connect_wait_s
        while self._monotonic() < deadline:
            if self._connection == "connected":
                break
            if self._connection == "failed" or not self._child_alive():
                self._fail(self._last_error or "discord_start_failed")
                return False
            self._sleep(min(0.05, max(0.0, deadline - self._monotonic())))
        if self._connection != "connected":
            self._fail(self._last_error or "discord_not_connected")
            return False
        try:
            sink = self._sink_factory()
            self._sink = sink
            sink.open()
            source = self._source_factory()
            self._source = source
            source.start()
        except Exception:
            self._fail("audio_bridge_failed")
            return False
        self._pacer = threading.Thread(target=self._pace_loop, name="hermes-discord-pcm", daemon=True)
        self._pacer.start()
        return True

    def is_running(self) -> bool:
        return (
            not self._closed.is_set()
            and self._child_alive()
            and self._connection in ("connecting", "connected")
        )

    def connected(self) -> bool:
        return self.is_running() and self._connection == "connected"

    def set_audio_enabled(self, enabled: bool) -> None:
        self._audio_enabled = bool(enabled)
        if not self._child_alive():
            return
        try:
            self._send_control({"op": "gate", "audio": self._audio_enabled})
            if not self._audio_enabled:
                self._flush_media()
        except OSError:
            self._fail("audio_bridge_failed")

    def stop(self) -> bool:
        self._closed.set()
        self._audio_enabled = False
        process = self._process
        if process is not None:
            self._reap_owned_child(process, wait_s=0.05)
        if self._sink is not None:
            with contextlib.suppress(Exception):
                self._sink.close()
            self._sink = None
        if self._source is not None:
            with contextlib.suppress(Exception):
                self._source.close()
            self._source = None
        for worker in (self._reader, self._pacer):
            if worker is not None and worker is not threading.current_thread():
                worker.join(timeout=1)
        if process is not None:
            self._close_child_streams(process)
        self._process = None
        self._reader = None
        self._pacer = None
        with self._lock:
            self._inbound.clear()
        self._connection = "idle"
        self._audience = "waiting_for_owner"
        self._last_inbound_at = None
        self._last_outbound_at = None
        self._last_cable_at = None
        self._media_failed = False
        return True

    def error(self) -> str | None:
        return self._last_error

    def diagnostics(self) -> dict[str, str]:
        now = self._monotonic()
        incoming = classify_activity(
            self._last_inbound_at,
            now,
            failed=self._media_failed,
            active="receiving",
            idle="silent",
            window_s=self._activity_window_s,
        )
        cable = classify_activity(
            self._last_cable_at,
            now,
            failed=self._media_failed,
            active="forwarding",
            idle="inactive",
            window_s=self._activity_window_s,
        )
        outgoing = classify_activity(
            self._last_outbound_at,
            now,
            failed=self._media_failed,
            active="sending",
            idle="silent",
            window_s=self._activity_window_s,
        )
        connection = self._connection if self._connection in CONNECTION_STATES else "failed"
        audience = self._audience if self._audience in AUDIENCE_STATES else "waiting_for_owner"
        return {
            "connection": connection,
            "audience": audience,
            "incoming": incoming if incoming in INCOMING_STATES else "silent",
            "cable": cable if cable in CABLE_STATES else "inactive",
            "outgoing": outgoing if outgoing in OUTGOING_STATES else "silent",
        }

    def _default_command(self) -> list[str] | None:
        node = shutil.which("node")
        if node is None or not SIDECAR_ENTRY.is_file():
            return None
        if not (SIDECAR_DIR / "node_modules" / "@discordjs" / "voice").is_dir():
            return None
        return [node, str(SIDECAR_ENTRY)]

    def _child_alive(self) -> bool:
        process = self._process
        return process is not None and process.poll() is None

    def _send_control(self, message: dict[str, Any]) -> None:
        self._write(encode_control(message))

    def _close_child_streams(self, process: subprocess.Popen) -> None:
        for stream in (process.stdin, process.stdout):
            if stream is None:
                continue
            with contextlib.suppress(Exception):
                stream.close()

    def _reap_owned_child(self, process: subprocess.Popen, wait_s: float) -> None:
        if process.poll() is not None:
            return
        try:
            process.wait(timeout=wait_s)
            return
        except subprocess.TimeoutExpired:
            pass
        with contextlib.suppress(OSError):
            process.terminate()
        try:
            process.wait(timeout=1)
            return
        except subprocess.TimeoutExpired:
            pass
        with contextlib.suppress(OSError):
            process.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=1)

    def _write(self, frame: bytes) -> None:
        if self._closed.is_set():
            raise OSError("sidecar stdin is closed")
        process = self._process
        if process is None or process.stdin is None:
            raise OSError("sidecar stdin is closed")
        acquired = self._write_lock.acquire(timeout=0.2)
        if not acquired:
            raise OSError("sidecar write lock timeout")
        try:
            if self._closed.is_set():
                raise OSError("sidecar stdin is closed")
            stdin = process.stdin
            if stdin is None:
                raise OSError("sidecar stdin is closed")
            try:
                written = stdin.write(frame)
                if written is None or written < len(frame):
                    remaining = frame if written is None else frame[written:]
                    os.write(stdin.fileno(), remaining)
                stdin.flush()
            except (OSError, ValueError) as exc:
                raise OSError("sidecar stdin is closed") from exc
        finally:
            self._write_lock.release()

    def _forwarding(self) -> bool:
        return self._audio_enabled and self._audience == "owner_present" and self._connection == "connected"

    def _flush_media(self) -> None:
        with self._lock:
            self._inbound.clear()
        source = self._source
        if source is not None and hasattr(source, "flush"):
            source.flush()
        sink = self._sink
        if sink is not None:
            sink.last_peak = 0.0

    def _fail(self, code: str) -> None:
        self._last_error = code
        self._connection = "failed"
        self._closed.set()
        process = self._process
        if process is not None:
            self._reap_owned_child(process, wait_s=0.05)
        if self._sink is not None:
            with contextlib.suppress(Exception):
                self._sink.close()
            self._sink = None
        if self._source is not None:
            with contextlib.suppress(Exception):
                self._source.close()
            self._source = None
        for worker in (self._reader, self._pacer):
            if worker is not None and worker is not threading.current_thread():
                worker.join(timeout=1)
        if process is not None:
            self._close_child_streams(process)
            self._process = None

    def _read_loop(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            while not self._closed.is_set():
                frame = read_frame(process.stdout)
                if frame is None:
                    break
                self._handle_frame(frame[0], frame[1])
        except ProtocolError:
            self._fail("discord_start_failed")
        except (OSError, ValueError):
            if not self._closed.is_set():
                self._fail("audio_bridge_failed")
        finally:
            if not self._closed.is_set() and self._connection != "failed":
                self._fail("audio_bridge_failed")

    def _handle_frame(self, frame_type: int, payload: bytes) -> None:
        if frame_type == TYPE_CONTROL:
            message = decode_control(payload)
            if message["op"] == "state":
                connection = str(message.get("connection", self._connection))
                audience = str(message.get("audience", self._audience))
                if connection in CONNECTION_STATES:
                    self._connection = connection
                if audience in AUDIENCE_STATES:
                    if audience != self._audience and audience != "owner_present":
                        self._flush_media()
                    self._audience = audience
                error = message.get("error")
                if error in {
                    "discord_permission_missing",
                    "discord_start_failed",
                    "discord_not_connected",
                    "discord_config_missing",
                    "discord_dependency_missing",
                    "audio_bridge_failed",
                }:
                    self._last_error = str(error)
                if connection == "failed":
                    self._fail(self._last_error or "discord_start_failed")
            elif message["op"] == "error":
                code = str(message.get("code", "discord_start_failed"))
                self._fail(code if code.startswith("discord_") or code == "audio_bridge_failed" else "discord_start_failed")
            return
        if frame_type == TYPE_PCM_IN:
            if len(payload) != PCM_PACKET_BYTES:
                return
            if not self._forwarding():
                return
            self._last_inbound_at = self._monotonic()
            with self._lock:
                self._inbound.append(payload)

    def _pace_loop(self) -> None:
        next_at = self._monotonic()
        while not self._closed.is_set():
            next_at += FRAME_INTERVAL_S
            delay = next_at - self._monotonic()
            if delay > 0:
                self._sleep(delay)
            if self._closed.is_set():
                return
            if not self._forwarding():
                self._flush_media()
                continue
            pcm_in = None
            with self._lock:
                if self._inbound:
                    pcm_in = self._inbound.popleft()
            if pcm_in is not None and self._sink is not None:
                try:
                    self._sink.write_pcm(pcm_in)
                    self._last_cable_at = self._monotonic()
                except Exception:
                    self._media_failed = True
                    self._fail("audio_bridge_failed")
                    return
            source = self._source
            if source is None:
                continue
            try:
                pcm_out = source.read(PCM_PACKET_BYTES)
            except Exception:
                self._media_failed = True
                self._fail("audio_bridge_failed")
                return
            if len(pcm_out) != PCM_PACKET_BYTES:
                continue
            try:
                self._write(encode_frame(TYPE_PCM_OUT, pcm_out))
                self._last_outbound_at = self._monotonic()
            except OSError:
                if not self._closed.is_set():
                    self._fail("audio_bridge_failed")
                return
