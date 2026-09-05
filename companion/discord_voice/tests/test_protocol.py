import unittest

from companion.discord_voice.protocol import (
    TYPE_CONTROL,
    TYPE_PCM_IN,
    FrameDecoder,
    ProtocolError,
    decode_control,
    encode_control,
    encode_frame,
    iter_frames,
)


class ProtocolTests(unittest.TestCase):
    def test_round_trip_control_and_pcm(self):
        control = encode_control({"op": "state", "connection": "connected", "audience": "owner_present"})
        pcm = encode_frame(TYPE_PCM_IN, b"\x01\x02" * 1920)
        frames = iter_frames([control[:3], control[3:] + pcm[:10], pcm[10:]])
        self.assertEqual(frames[0][0], TYPE_CONTROL)
        self.assertEqual(decode_control(frames[0][1])["op"], "state")
        self.assertEqual(frames[1][0], TYPE_PCM_IN)
        self.assertEqual(len(frames[1][1]), 3840)

    def test_rejects_oversized_and_unknown_type(self):
        decoder = FrameDecoder()
        with self.assertRaises(ProtocolError):
            decoder.push(b"\xff\xff\xff\x7f\x01")
        with self.assertRaises(ProtocolError):
            decoder.push(b"\x02\x00\x00\x00\x09X")

    def test_rejects_incomplete_close(self):
        decoder = FrameDecoder()
        decoder.push(b"\x05\x00\x00\x00\x01ab")
        with self.assertRaises(ProtocolError):
            decoder.close()


if __name__ == "__main__":
    unittest.main()
