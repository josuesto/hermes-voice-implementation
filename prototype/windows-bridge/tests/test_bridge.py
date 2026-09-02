import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bridge


class ClassifyTests(unittest.TestCase):
    def test_vb_cable_is_injection_class(self):
        self.assertEqual(bridge.classify_name("CABLE Output (VB-Audio Virtual Cable)"), "vb-cable")

    def test_wasapi_loopback_is_not_injection(self):
        self.assertEqual(bridge.classify_name("Speakers", is_loopback=True), "loopback")
        self.assertFalse(
            bridge.has_programmable_mic([{"kind": "capture", "class": "loopback", "_loopback": True}])
        )

    def test_stereo_mix_is_not_programmable_injection(self):
        self.assertEqual(bridge.classify_name("Stereo Mix"), "stereo-mix")
        rows = [
            {
                "kind": "capture",
                "class": "stereo-mix",
            }
        ]
        self.assertFalse(bridge.has_programmable_mic(rows))


class ToneTests(unittest.TestCase):
    def test_tone_length_matches_seconds(self):
        tone = bridge.generate_tone(0.25, samplerate=16000)
        self.assertEqual(len(tone), 4000)

    def test_tone_is_not_silent(self):
        tone = bridge.generate_tone(0.1, samplerate=8000)
        self.assertGreater(float(abs(tone).max()), 0.05)

    def test_mono_input_is_duplicated_for_stereo_cable(self):
        import numpy as np

        source = np.array([[0.25], [-0.5]], dtype=np.float32)
        routed = bridge._adapt_channels(source, 2)
        self.assertEqual(routed.shape, (2, 2))
        np.testing.assert_array_equal(routed[:, 0], routed[:, 1])

    def test_stereo_input_is_mixed_for_mono_sink(self):
        import numpy as np

        source = np.array([[0.25, 0.75], [-0.5, 0.5]], dtype=np.float32)
        routed = bridge._adapt_channels(source, 1)
        np.testing.assert_allclose(routed[:, 0], [0.5, 0.0])


class ListSanitizeTests(unittest.TestCase):
    def test_sanitize_row_drops_name(self):
        row = {
            "index": 3,
            "kind": "capture",
            "class": "physical-or-other",
            "default": True,
            "hostapi": "Windows WASAPI",
            "name": "Secret Mic",
            "id_token": "abc123abc123",
        }
        cleaned = bridge.sanitize_row(row)
        self.assertNotIn("name", cleaned)
        self.assertEqual(cleaned["index"], 3)
        self.assertEqual(cleaned["id_token"], "abc123abc123")

    def test_programmable_mic_true_for_vb_cable_capture(self):
        rows = [
            {"kind": "playback", "class": "vb-cable"},
            {"kind": "capture", "class": "vb-cable"},
        ]
        self.assertTrue(bridge.has_programmable_mic(rows))


class SessionRestoreTests(unittest.TestCase):
    def test_restore_without_snapshot_is_noop(self):
        bridge._SNAPSHOT = None
        self.assertEqual(bridge.cmd_restore(), 0)

    def test_stop_when_idle_succeeds(self):
        path = bridge.session_path()
        if path.exists():
            path.unlink()
        self.assertEqual(bridge.cmd_stop(), 0)
        self.assertFalse(bridge.session_running())

    def test_id_token_is_stable_and_short(self):
        first = bridge.id_token(1, "capture", "label")
        second = bridge.id_token(1, "capture", "label")
        other = bridge.id_token(2, "capture", "label")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 12)
        self.assertNotEqual(first, other)


class ProcessSafetyTests(unittest.TestCase):
    def setUp(self):
        bridge._MONITOR_ACTIVE = False
    def test_source_has_no_force_kill(self):
        source = Path(bridge.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("taskkill", source)
        self.assertNotIn("_kill_pid", source)
        self.assertNotIn("popen", source)
        self.assertNotIn("subprocess", source)

    def test_forged_pid_in_temp_files_does_not_terminate(self):
        session = bridge.session_path()
        pid_file = session.with_suffix(".pid")
        session.write_text(json.dumps({"running": True, "pid": 4}), encoding="utf-8")
        pid_file.write_text("4", encoding="utf-8")
        self.addCleanup(lambda: pid_file.exists() and pid_file.unlink())
        with (
            patch.object(bridge.os, "kill") as mock_kill,
            patch.object(subprocess, "run") as mock_run,
            patch.object(subprocess, "Popen") as mock_popen,
            patch.object(subprocess, "call") as mock_call,
        ):
            code = bridge.cmd_stop()
        self.assertEqual(code, 0)
        mock_kill.assert_not_called()
        mock_run.assert_not_called()
        mock_popen.assert_not_called()
        mock_call.assert_not_called()

    def test_start_without_seconds_does_not_spawn(self):
        with (
            patch.object(bridge.os, "kill") as mock_kill,
            patch.object(subprocess, "run") as mock_run,
            patch.object(subprocess, "Popen") as mock_popen,
        ):
            code = bridge.cmd_start(seconds=None)
        self.assertEqual(code, 2)
        mock_kill.assert_not_called()
        mock_run.assert_not_called()
        mock_popen.assert_not_called()

    def test_route_requires_positive_duration_before_device_access(self):
        with patch.object(bridge, "_route_devices") as route_devices:
            code = bridge.cmd_route_mic(source=7, seconds=0)
        self.assertEqual(code, 2)
        route_devices.assert_not_called()


if __name__ == "__main__":
    unittest.main()
