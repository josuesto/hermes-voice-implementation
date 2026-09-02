import asyncio
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from aiohttp.test_utils import TestClient, TestServer
from aiortc import RTCPeerConnection, RTCSessionDescription

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from companion.browser_call import server
from companion.browser_call.host import OwnedBrowserHost


class DeviceSelectionTests(unittest.TestCase):
    def test_selects_exact_wasapi_cable(self):
        hostapis = [{"name": "MME"}, {"name": "Windows WASAPI"}]
        devices = [
            {"name": server.CABLE_INPUT_NAME, "hostapi": 0, "max_output_channels": 2},
            {"name": server.CABLE_INPUT_NAME, "hostapi": 1, "max_output_channels": 2},
        ]
        self.assertEqual(server.pick_wasapi_output(devices, hostapis), 1)

    def test_ambiguous_or_missing_cable_refuses(self):
        hostapis = [{"name": "Windows WASAPI"}]
        duplicate = [
            {"name": server.CABLE_INPUT_NAME, "hostapi": 0, "max_output_channels": 2},
            {"name": server.CABLE_INPUT_NAME, "hostapi": 0, "max_output_channels": 2},
        ]
        with self.assertRaises(RuntimeError):
            server.pick_wasapi_output(duplicate, hostapis)
        with self.assertRaises(RuntimeError):
            server.pick_wasapi_output([], hostapis)


class CodexProcessSelectionTests(unittest.TestCase):
    def test_selects_one_current_session_codex_main_window(self):
        rows = [
            {
                "visible": True,
                "owner": False,
                "class_name": "Chrome_WidgetWin_1",
                "process_name": "ChatGPT.exe",
                "session_id": 7,
                "pid": 42,
            },
            {
                "visible": True,
                "owner": False,
                "class_name": "OtherWindow",
                "process_name": "other.exe",
                "session_id": 7,
                "pid": 99,
            },
        ]
        self.assertEqual(server.pick_unique_codex_process(rows, 7), 42)

    def test_ambiguous_or_other_session_refuses(self):
        candidate = {
            "visible": True,
            "owner": False,
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "chatgpt.exe",
            "session_id": 7,
            "pid": 42,
        }
        with self.assertRaises(RuntimeError):
            server.pick_unique_codex_process([candidate, dict(candidate, pid=43)], 7)
        with self.assertRaises(RuntimeError):
            server.pick_unique_codex_process([candidate], 8)


class FakeProcessSource:
    instances = []

    def __init__(self):
        self.started = False
        self.closed = False
        self.sample = 1200
        self.__class__.instances.append(self)

    def start(self):
        self.started = True

    def read(self, byte_count):
        frame_count = byte_count // server.PCM_BYTES_PER_FRAME
        samples = np.full((frame_count, 2), self.sample, dtype="<i2")
        return samples.tobytes()

    def close(self):
        self.closed = True


class CodexProcessTrackTests(unittest.IsolatedAsyncioTestCase):
    async def test_pcm_is_returned_and_source_is_closed(self):
        FakeProcessSource.instances.clear()
        track = server.CodexProcessAudioTrack(source_factory=FakeProcessSource)
        frame = await track.recv()
        self.assertEqual(frame.sample_rate, server.SAMPLE_RATE)
        self.assertGreater(int(np.abs(frame.to_ndarray()).max()), 0)
        track.stop()
        self.assertTrue(FakeProcessSource.instances[0].started)
        self.assertTrue(FakeProcessSource.instances[0].closed)


class ToneTrackTests(unittest.IsolatedAsyncioTestCase):
    async def test_track_is_silent_until_explicit_trigger(self):
        track = server.TestToneTrack()
        silent = await track.recv()
        self.assertEqual(int(np.abs(silent.to_ndarray()).max()), 0)
        track.trigger()
        audible = await track.recv()
        self.assertGreater(int(np.abs(audible.to_ndarray()).max()), 0)
        track.stop()


class PageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (server.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        cls.js = (server.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    def test_minimal_controls_exist(self):
        for label in ("Mute microphone", "Mute Codex audio", "Leave call"):
            self.assertIn(label, self.html)
        self.assertNotIn("End session", self.html)

    def test_feature_detection_and_no_hardcoded_ice_server(self):
        self.assertIn("RTCPeerConnection", self.js)
        self.assertIn("getUserMedia", self.js)
        self.assertIn("isSecureContext", self.js)
        self.assertIn("iceServers: []", self.js)
        self.assertGreaterEqual(self.js.count('iceGatheringState === "complete"'), 2)
        self.assertIn("window.setTimeout(finish, 2000)", self.js)

    def test_page_contains_no_inline_script(self):
        self.assertNotIn("<script>", self.html)
        self.assertIn('src="/app.js"', self.html)


class ServerStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_is_idempotent(self):
        call_server = server.BrowserCallServer()
        await call_server.close()
        await call_server.close()
        self.assertFalse(call_server.active)


class ProcessLoopbackSourceTests(unittest.TestCase):
    def test_read_pads_silence_and_bounds_buffer(self):
        source = server.ProcessLoopbackSource()
        with source._lock:
            source._buffer.extend(b"\x01\x00\x02\x00")
        padded = source.read(12)
        self.assertEqual(len(padded), 12)
        self.assertEqual(padded[:4], b"\x01\x00\x02\x00")
        self.assertEqual(padded[4:], b"\x00" * 8)
        source.close()

    def test_header_timeout_stops_owned_child(self):
        created = []

        class FakeStdout:
            def read(self, _n):
                time.sleep(2)
                return b""

            def close(self):
                return None

        class FakeStdin:
            def write(self, _data):
                return 1

            def flush(self):
                return None

            def close(self):
                return None

        class FakeProc:
            def __init__(self):
                self.stdin = FakeStdin()
                self.stdout = FakeStdout()
                self.stderr = None
                self.killed = False
                self._code = None

            def poll(self):
                return self._code

            def wait(self, timeout=None):
                if self._code is None:
                    raise subprocess.TimeoutExpired(cmd="helper", timeout=timeout)
                return self._code

            def terminate(self):
                self.kill()

            def kill(self):
                self.killed = True
                self._code = 1

        def fake_popen(*_args, **_kwargs):
            proc = FakeProc()
            created.append(proc)
            return proc

        source = server.ProcessLoopbackSource()
        with patch.object(server, "ensure_process_loopback_helper", return_value=Path("helper.exe")):
            with patch.object(server, "find_unique_codex_process", return_value=42):
                with patch.object(subprocess, "Popen", fake_popen):
                    with self.assertRaises((TimeoutError, RuntimeError)):
                        source.start(header_timeout_s=0.2)
        self.assertTrue(created[0].killed)
        self.assertTrue(source._closed)


class CloseOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_stops_outgoing_even_if_consume_hangs(self):
        class HangingSink:
            def __init__(self):
                self.closed = False

            async def consume(self, _track):
                await asyncio.Event().wait()

            def close(self):
                self.closed = True

        class FakeOutgoing:
            def __init__(self):
                self.stopped = False

            def stop(self):
                self.stopped = True

        call_server = server.BrowserCallServer()
        sink = HangingSink()
        outgoing = FakeOutgoing()
        hang = asyncio.create_task(sink.consume(None))
        call_server._sink = sink
        call_server._outgoing = outgoing
        call_server._tasks.add(hang)
        await asyncio.wait_for(call_server.close(), timeout=1)
        self.assertTrue(outgoing.stopped)
        self.assertTrue(sink.closed)
        self.assertFalse(call_server.active)


class FakeSink:
    instances = []

    def __init__(self):
        self.received = asyncio.Event()
        self.closed = False
        self.__class__.instances.append(self)

    async def consume(self, track):
        await track.recv()
        self.received.set()
        while True:
            await track.recv()

    def close(self):
        self.closed = True


class WebRtcIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeSink.instances.clear()
        FakeProcessSource.instances.clear()
        self.call_server = server.BrowserCallServer(
            sink_factory=FakeSink,
            source_factory=FakeProcessSource,
        )
        self.client = TestClient(TestServer(server.build_app(self.call_server)))
        await self.client.start_server()
        self.peer = RTCPeerConnection()

    async def asyncTearDown(self):
        await self.peer.close()
        await self.client.close()

    async def test_one_peer_negotiates_both_audio_directions_and_ends(self):
        incoming_track = server.TestToneTrack()
        self.peer.addTrack(incoming_track)
        remote_tracks = []

        @self.peer.on("track")
        def on_track(track):
            if track.kind == "audio":
                remote_tracks.append(track)

        offer = await self.peer.createOffer()
        await self.peer.setLocalDescription(offer)
        response = await self.client.post(
            "/offer",
            json={"sdp": self.peer.localDescription.sdp, "type": self.peer.localDescription.type},
        )
        self.assertEqual(response.status, 200)
        answer = await response.json()
        await self.peer.setRemoteDescription(
            RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
        )

        self.assertEqual(len(FakeSink.instances), 1)
        await asyncio.wait_for(FakeSink.instances[0].received.wait(), timeout=5)
        self.assertEqual(len(remote_tracks), 1)

        tone_response = await self.client.post("/test-tone")
        self.assertEqual(tone_response.status, 200)
        audible = False
        for _ in range(12):
            frame = await asyncio.wait_for(remote_tracks[0].recv(), timeout=2)
            if int(np.abs(frame.to_ndarray()).max()) > 0:
                audible = True
                break
        self.assertTrue(audible)

        end_response = await self.client.post("/end")
        self.assertEqual(end_response.status, 200)
        self.assertFalse(self.call_server.active)
        self.assertTrue(FakeSink.instances[0].closed)
        self.assertFalse(FakeProcessSource.instances[0].closed)
        page = await self.client.get("/")
        self.assertEqual(page.status, 200)

    async def test_leave_call_allows_reconnect_without_stopping_capture(self):
        incoming_track = server.TestToneTrack()
        self.peer.addTrack(incoming_track)
        offer = await self.peer.createOffer()
        await self.peer.setLocalDescription(offer)
        first = await self.client.post(
            "/offer",
            json={"sdp": self.peer.localDescription.sdp, "type": self.peer.localDescription.type},
        )
        self.assertEqual(first.status, 200)
        self.assertTrue(FakeProcessSource.instances[0].started)
        leave = await self.client.post("/end")
        self.assertEqual(leave.status, 200)
        self.assertFalse(self.call_server.active)
        self.assertFalse(FakeProcessSource.instances[0].closed)

        peer2 = RTCPeerConnection()
        peer2.addTrack(server.TestToneTrack())
        offer2 = await peer2.createOffer()
        await peer2.setLocalDescription(offer2)
        second = await self.client.post(
            "/offer",
            json={"sdp": peer2.localDescription.sdp, "type": peer2.localDescription.type},
        )
        self.assertEqual(second.status, 200)
        self.assertTrue(self.call_server.active)
        self.assertEqual(len(FakeProcessSource.instances), 1)
        self.assertFalse(FakeProcessSource.instances[0].closed)
        await peer2.close()


class CaptureShutdownTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_close_releases_capture_after_leave(self):
        FakeProcessSource.instances.clear()
        call_server = server.BrowserCallServer(source_factory=FakeProcessSource)
        call_server._capture = FakeProcessSource()
        call_server._capture.start()
        await call_server.leave()
        self.assertFalse(FakeProcessSource.instances[0].closed)
        await call_server.close()
        self.assertTrue(FakeProcessSource.instances[0].closed)


def _ephemeral_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class OwnedHostTests(unittest.TestCase):
    def test_start_stop_and_port_conflict(self):
        occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        occupied.bind(("127.0.0.1", 0))
        port = int(occupied.getsockname()[1])
        blocked = OwnedBrowserHost(port=port)
        self.assertFalse(blocked.start())
        self.assertEqual(blocked.error(), "browser_start_failed")
        occupied.close()

        host = OwnedBrowserHost(port=_ephemeral_port())
        self.assertTrue(host.start())
        self.assertTrue(host.is_running())
        self.assertTrue(host.stop())
        self.assertFalse(host.is_running())

    def test_dead_server_is_not_running(self):
        host = OwnedBrowserHost(port=_ephemeral_port())
        self.assertTrue(host.start())
        loop = host._loop
        thread = host._thread
        self.assertIsNotNone(loop)
        self.assertIsNotNone(thread)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=8)
        self.assertFalse(host.is_running())
        host.stop()


if __name__ == "__main__":
    unittest.main()
