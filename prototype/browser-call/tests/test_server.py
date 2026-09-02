import asyncio
import sys
import unittest
from pathlib import Path

import numpy as np
from aiohttp.test_utils import TestClient, TestServer
from aiortc import RTCPeerConnection, RTCSessionDescription

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server


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
        for label in ("Mute microphone", "Mute Codex audio", "End session"):
            self.assertIn(label, self.html)

    def test_feature_detection_and_no_hardcoded_ice_server(self):
        self.assertIn("RTCPeerConnection", self.js)
        self.assertIn("getUserMedia", self.js)
        self.assertIn("isSecureContext", self.js)
        self.assertIn("iceServers: []", self.js)

    def test_page_contains_no_inline_script(self):
        self.assertNotIn("<script>", self.html)
        self.assertIn('src="/app.js"', self.html)


class ServerStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_is_idempotent(self):
        call_server = server.BrowserCallServer()
        await call_server.close()
        await call_server.close()
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
        self.call_server = server.BrowserCallServer(sink_factory=FakeSink)
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


if __name__ == "__main__":
    unittest.main()
