import test from "node:test";
import assert from "node:assert/strict";
import {
  decodeControl,
  encodeControl,
  encodeFrame,
  FrameDecoder,
  ProtocolError,
  TYPE_PCM_IN,
} from "../src/protocol.mjs";

test("control and pcm frames round-trip across chunks", () => {
  const control = encodeControl({ op: "state", connection: "connected", audience: "owner_present" });
  const pcm = encodeFrame(TYPE_PCM_IN, Buffer.alloc(3840, 7));
  const decoder = new FrameDecoder();
  const first = decoder.push(control.subarray(0, 5));
  assert.equal(first.length, 0);
  const rest = decoder.push(Buffer.concat([control.subarray(5), pcm]));
  assert.equal(rest.length, 2);
  assert.equal(decodeControl(rest[0].payload).op, "state");
  assert.equal(rest[1].payload.length, 3840);
});

test("malformed length is rejected", () => {
  const decoder = new FrameDecoder();
  assert.throws(() => decoder.push(Buffer.from([0xff, 0xff, 0xff, 0x7f, 0x01])), ProtocolError);
});
