import unittest

import numpy as np

from companion.audio_io import (
    PCM_PACKET_BYTES,
    CableAudioSink,
    pick_unique_codex_process,
    pick_wasapi_output,
)


class AudioIoTests(unittest.TestCase):
    def test_write_pcm_matches_known_s16le_bytes(self):
        written = []

        class Stream:
            channels = 2

            def write(self, data):
                written.append(np.array(data, copy=True))

        sink = CableAudioSink()
        sink._stream = Stream()
        pcm = (np.array([[1000, -2000]], dtype="<i2")).tobytes()
        sink.write_pcm(pcm)
        self.assertEqual(len(written), 1)
        packed = written[0]
        self.assertEqual(packed.shape, (1, 2))
        self.assertAlmostEqual(float(packed[0, 0]), 1000 / 32768.0, places=6)
        self.assertAlmostEqual(float(packed[0, 1]), -2000 / 32768.0, places=6)
        self.assertEqual(len(pcm) % 4, 0)
        self.assertLess(len(pcm), PCM_PACKET_BYTES)

    def test_wasapi_and_codex_selection_stay_strict(self):
        hostapis = [{"name": "Windows WASAPI"}]
        devices = [{"name": "CABLE Input (VB-Audio Virtual Cable)", "hostapi": 0, "max_output_channels": 2}]
        self.assertEqual(pick_wasapi_output(devices, hostapis), 0)
        pid = pick_unique_codex_process(
            [
                {
                    "visible": True,
                    "owner": False,
                    "class_name": "Chrome_WidgetWin_1",
                    "process_name": "chatgpt.exe",
                    "session_id": 1,
                    "pid": 9,
                }
            ],
            1,
        )
        self.assertEqual(pid, 9)


if __name__ == "__main__":
    unittest.main()
