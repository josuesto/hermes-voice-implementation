import test from "node:test";
import assert from "node:assert/strict";
import {
  applyVoiceEvent,
  enqueueFrame,
  flushBoundedQueue,
  writeWithBackpressure,
} from "../src/audience.mjs";

const CONFIGURED = "channel-configured";
const MOVED = "channel-elsewhere";

function readyOnConfigured(overrides = {}) {
  return applyVoiceEvent({
    audioEnabled: true,
    configuredChannelId: CONFIGURED,
    ownerId: "owner",
    botId: "bot",
    botChannelId: CONFIGURED,
    connectionReady: true,
    configuredMemberIds: ["owner", "bot"],
    previousConnectionReady: true,
    ...overrides,
  });
}

test("ready voice connection on the configured channel authorizes owner-only media", () => {
  const result = readyOnConfigured();
  assert.equal(result.audience, "owner_present");
  assert.equal(result.connection, "connected");
  assert.equal(result.forwarding, true);
  assert.equal(result.shouldPause, false);
  assert.equal(result.shouldAbandonMovedChannel, false);
  assert.equal(result.shouldReconnectToConfigured, false);
});

test("owner still in the configured channel does not authorize a moved bot", () => {
  const result = applyVoiceEvent({
    audioEnabled: true,
    configuredChannelId: CONFIGURED,
    ownerId: "owner",
    botId: "bot",
    botChannelId: MOVED,
    connectionReady: true,
    configuredMemberIds: ["owner", "bot"],
    previousConnectionReady: true,
  });
  assert.equal(result.forwarding, false);
  assert.equal(result.shouldPause, true);
  assert.equal(result.shouldAbandonMovedChannel, true);
  assert.equal(result.shouldReconnectToConfigured, true);
  assert.equal(result.connection, "connecting");
  assert.equal(result.audience, "waiting_for_owner");
});

test("stale owner-only membership without the bot present does not forward", () => {
  const result = applyVoiceEvent({
    audioEnabled: true,
    configuredChannelId: CONFIGURED,
    ownerId: "owner",
    botId: "bot",
    botChannelId: null,
    connectionReady: false,
    configuredMemberIds: ["owner"],
    previousConnectionReady: false,
  });
  assert.equal(result.audience, "waiting_for_owner");
  assert.equal(result.forwarding, false);
  assert.equal(result.shouldPause, true);
  assert.equal(result.shouldAbandonMovedChannel, false);
});

test("disconnect after Ready pauses and reconnects only to the configured channel", () => {
  const result = applyVoiceEvent({
    audioEnabled: true,
    configuredChannelId: CONFIGURED,
    ownerId: "owner",
    botId: "bot",
    botChannelId: null,
    connectionReady: false,
    configuredMemberIds: ["owner"],
    previousConnectionReady: true,
  });
  assert.equal(result.forwarding, false);
  assert.equal(result.shouldPause, true);
  assert.equal(result.shouldReconnectToConfigured, true);
  assert.equal(result.shouldAbandonMovedChannel, false);
  assert.equal(result.connection, "connecting");
});

test("kick with extras still blocked never follows the moved audience", () => {
  const result = applyVoiceEvent({
    audioEnabled: true,
    configuredChannelId: CONFIGURED,
    ownerId: "owner",
    botId: "bot",
    botChannelId: MOVED,
    connectionReady: true,
    configuredMemberIds: ["owner", "bot", "extra"],
    previousConnectionReady: true,
  });
  assert.equal(result.audience, "audience_blocked");
  assert.equal(result.forwarding, false);
  assert.equal(result.shouldAbandonMovedChannel, true);
});

test("flushBoundedQueue keeps remaining frames when write returns false", () => {
  const written = [];
  const stream = {
    writable: true,
    writableNeedDrain: false,
    write(frame) {
      written.push(frame);
      this.writableNeedDrain = true;
      return false;
    },
  };
  const queue = [
    Buffer.alloc(4, 1),
    Buffer.alloc(4, 2),
    Buffer.alloc(4, 3),
  ];
  const remaining = flushBoundedQueue(queue, stream);
  assert.equal(written.length, 1);
  assert.equal(written[0][0], 1);
  assert.equal(remaining.length, 2);
  assert.equal(remaining[0][0], 2);
});

test("writeWithBackpressure refuses a stream that already needs drain", () => {
  const stream = {
    writable: true,
    writableNeedDrain: true,
    write() {
      throw new Error("must not write while drained");
    },
  };
  const result = writeWithBackpressure(stream, Buffer.alloc(4, 9));
  assert.equal(result.accepted, false);
  assert.equal(result.waitDrain, true);
});

test("enqueue still drops oldest while waiting for drain", () => {
  let queue = [];
  queue = enqueueFrame(queue, Buffer.alloc(4, 1));
  queue = enqueueFrame(queue, Buffer.alloc(4, 2));
  queue = enqueueFrame(queue, Buffer.alloc(4, 3));
  queue = enqueueFrame(queue, Buffer.alloc(4, 4));
  assert.equal(queue.length, 3);
  assert.equal(queue[0][0], 2);
});
