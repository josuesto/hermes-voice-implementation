import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from companion.audio_io import PCM_PACKET_BYTES
from companion.discord_voice.transport import DiscordConfig, DiscordVoiceTransport, classify_activity

FAKE = Path(__file__).resolve().parent / "fake_sidecar.py"
PYTHON = sys.executable
KNOWN_IN = (b"\x11\x22" * (PCM_PACKET_BYTES // 2))[:PCM_PACKET_BYTES]
KNOWN_OUT = (b"\x33\x44" * (PCM_PACKET_BYTES // 2))[:PCM_PACKET_BYTES]
CONFIG = DiscordConfig(
    token="test-token",
    guild_id="123456789012345678",
    channel_id="234567890123456789",
    owner_id="345678901234567890",
)


class FakeSink:
    def __init__(self):
        self.writes: list[bytes] = []
        self.opened = False
        self.closed = False
        self.last_peak = 0.0
        self.last_write_at = None
        self.failed = False

    def open(self):
        self.opened = True

    def write_pcm(self, pcm: bytes):
        self.writes.append(pcm)

    def close(self):
        self.closed = True


class FailingSource:
    def __init__(self):
        self.started = False
        self.closed = False
        self.flushed = 0

    def start(self, header_timeout_s: float = 15.0):
        del header_timeout_s
        raise RuntimeError("capture failed")

    def read(self, byte_count: int) -> bytes:
        del byte_count
        return b""

    def flush(self):
        self.flushed += 1

    def close(self):
        self.closed = True


class FakeSource:
    def __init__(self, payload: bytes = KNOWN_OUT):
        self.payload = payload
        self.started = False
        self.closed = False
        self.flushed = 0

    def start(self, header_timeout_s: float = 15.0):
        del header_timeout_s
        self.started = True

    def read(self, byte_count: int) -> bytes:
        return self.payload[:byte_count]

    def flush(self):
        self.flushed += 1

    def close(self):
        self.closed = True


def _transport(mode="ready", audience="owner_present", record=None, echo=False, window=0.4):
    env_prefix = {}
    command = [PYTHON, str(FAKE)]
    extra_env = {
        "FAKE_SIDECAR_MODE": mode,
        "FAKE_SIDECAR_AUDIENCE": audience,
    }
    if record:
        extra_env["FAKE_SIDECAR_RECORD"] = str(record)
    if echo:
        extra_env["FAKE_SIDECAR_ECHO"] = "1"
    old = {key: os.environ.get(key) for key in extra_env}
    os.environ.update(extra_env)
    sink = FakeSink()
    source = FakeSource()
    transport = DiscordVoiceTransport(
        config=CONFIG,
        command=command,
        sink_factory=lambda: sink,
        source_factory=lambda: source,
        connect_wait_s=2.0,
        activity_window_s=window,
    )
    return transport, sink, source, old


def _restore(old):
    for key, value in old.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class DiscordTransportTests(unittest.TestCase):
    def test_known_pcm_each_way_with_fake_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "out.pcm"
            transport, sink, source, old = _transport(record=record)
            try:
                self.assertTrue(transport.start())
                self.assertTrue(transport.connected())
                self.assertEqual(transport.diagnostics()["incoming"], "silent")
                transport.set_audio_enabled(True)
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and not sink.writes:
                    time.sleep(0.02)
                self.assertEqual(sink.writes[0], KNOWN_IN)
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and not record.exists():
                    time.sleep(0.02)
                self.assertTrue(record.exists())
                self.assertEqual(record.read_bytes()[:PCM_PACKET_BYTES], KNOWN_OUT)
                self.assertTrue(source.started)
                self.assertTrue(transport.stop())
                self.assertTrue(sink.closed)
                self.assertTrue(source.closed)
                self.assertFalse(transport.is_running())
            finally:
                transport.stop()
                _restore(old)

    def test_audio_stays_gated_until_enabled(self):
        transport, sink, source, old = _transport()
        try:
            self.assertTrue(transport.start())
            time.sleep(0.15)
            self.assertEqual(sink.writes, [])
            self.assertFalse(transport._audio_enabled)
            self.assertGreaterEqual(source.flushed, 1)
            self.assertNotIn("url", transport.diagnostics())
            self.assertNotIn("token", str(transport.diagnostics()))
        finally:
            transport.stop()
            _restore(old)

    def test_audience_block_flushes_and_discards(self):
        transport, sink, source, old = _transport(audience="audience_blocked")
        try:
            self.assertTrue(transport.start())
            transport.set_audio_enabled(True)
            time.sleep(0.2)
            self.assertEqual(sink.writes, [])
            self.assertGreaterEqual(source.flushed, 1)
            self.assertEqual(transport.diagnostics()["audience"], "audience_blocked")
        finally:
            transport.stop()
            _restore(old)

    def test_malformed_pipe_fails_closed(self):
        transport, _sink, _source, old = _transport(mode="malformed")
        try:
            self.assertFalse(transport.start())
            self.assertEqual(transport.error(), "discord_start_failed")
            self.assertFalse(transport.is_running())
        finally:
            transport.stop()
            _restore(old)

    def test_child_exit_is_detected(self):
        transport, _sink, _source, old = _transport(mode="exit")
        try:
            started = transport.start()
            if started:
                deadline = time.monotonic() + 2.0
                while time.monotonic() < deadline and transport.is_running():
                    time.sleep(0.02)
            self.assertFalse(transport.is_running())
        finally:
            transport.stop()
            _restore(old)

    def test_missing_config_fails_closed(self):
        transport = DiscordVoiceTransport(command=[PYTHON, str(FAKE)], env={})
        self.assertFalse(transport.start())
        self.assertEqual(transport.error(), "discord_config_missing")

    def test_activity_expires_to_silent(self):
        now = 100.0
        self.assertEqual(
            classify_activity(99.9, now, failed=False, active="receiving", idle="silent", window_s=0.4),
            "receiving",
        )
        self.assertEqual(
            classify_activity(99.0, now, failed=False, active="receiving", idle="silent", window_s=0.4),
            "silent",
        )
        self.assertEqual(
            classify_activity(99.9, now, failed=True, active="receiving", idle="silent"),
            "failed",
        )

    def test_status_rejects_identifiers(self):
        transport, _sink, _source, old = _transport()
        try:
            self.assertTrue(transport.start())
            snapshot = transport.diagnostics()
            dumped = str(snapshot)
            self.assertNotIn(CONFIG.token, dumped)
            self.assertNotIn(CONFIG.guild_id, dumped)
            self.assertNotIn(CONFIG.channel_id, dumped)
            self.assertNotIn(CONFIG.owner_id, dumped)
            self.assertEqual(set(snapshot), {"connection", "audience", "incoming", "cable", "outgoing"})
        finally:
            transport.stop()
            _restore(old)

    def test_stop_unblocks_stuck_pipe_writer(self):
        transport, sink, source, old = _transport(mode="hold")
        child = None
        try:
            self.assertTrue(transport.start())
            child = transport._process
            self.assertIsNotNone(child)
            self.assertIsNone(child.poll())
            transport.set_audio_enabled(True)
            time.sleep(0.8)
            started = time.monotonic()
            self.assertTrue(transport.stop())
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 5.0)
            self.assertFalse(transport.is_running())
            self.assertTrue(sink.closed)
            self.assertTrue(source.closed)
            self.assertIsNone(transport._process)
            self.assertIsNone(transport._reader)
            self.assertIsNone(transport._pacer)
            self.assertIsNotNone(child.poll())
        finally:
            transport.stop()
            if child is not None and child.poll() is None:
                child.kill()
                child.wait(timeout=1)
            _restore(old)

    def test_source_start_failure_closes_opened_sink_and_child(self):
        extra_env = {
            "FAKE_SIDECAR_MODE": "ready",
            "FAKE_SIDECAR_AUDIENCE": "owner_present",
        }
        old = {key: os.environ.get(key) for key in extra_env}
        os.environ.update(extra_env)
        sink = FakeSink()
        source = FailingSource()
        transport = DiscordVoiceTransport(
            config=CONFIG,
            command=[PYTHON, str(FAKE)],
            sink_factory=lambda: sink,
            source_factory=lambda: source,
            connect_wait_s=2.0,
        )
        try:
            self.assertFalse(transport.start())
            self.assertEqual(transport.error(), "audio_bridge_failed")
            self.assertTrue(sink.opened)
            self.assertTrue(sink.closed)
            self.assertTrue(source.closed)
            self.assertFalse(source.started)
            self.assertFalse(transport.is_running())
            self.assertIsNone(transport._process)
        finally:
            transport.stop()
            _restore(old)


if __name__ == "__main__":
    unittest.main()
