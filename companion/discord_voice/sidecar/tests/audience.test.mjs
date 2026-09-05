import test from "node:test";
import assert from "node:assert/strict";
import {
  classifyAudience,
  enqueueFrame,
  flushQueue,
  shouldForwardAudio,
  shouldSubscribe,
} from "../src/audience.mjs";

test("owner-only subscribe excludes the bot and anyone else", () => {
  assert.equal(shouldSubscribe({ userId: "owner", ownerId: "owner", botId: "bot" }), true);
  assert.equal(shouldSubscribe({ userId: "bot", ownerId: "owner", botId: "bot" }), false);
  assert.equal(shouldSubscribe({ userId: "other", ownerId: "owner", botId: "bot" }), false);
});

test("audience distinguishes waiting, owner, and extra participants", () => {
  assert.equal(
    classifyAudience({ memberIds: ["bot"], ownerId: "owner", botId: "bot" }),
    "waiting_for_owner",
  );
  assert.equal(
    classifyAudience({ memberIds: ["owner", "bot"], ownerId: "owner", botId: "bot" }),
    "owner_present",
  );
  assert.equal(
    classifyAudience({ memberIds: ["owner", "bot", "extra"], ownerId: "owner", botId: "bot" }),
    "audience_blocked",
  );
  assert.equal(
    classifyAudience({ memberIds: ["owner"], ownerId: "owner", botId: "bot" }),
    "waiting_for_owner",
  );
});

test("pause drops queued frames instead of replaying them", () => {
  let queue = enqueueFrame([], Buffer.alloc(3840, 1));
  queue = enqueueFrame(queue, Buffer.alloc(3840, 2));
  queue = enqueueFrame(queue, Buffer.alloc(3840, 3));
  queue = enqueueFrame(queue, Buffer.alloc(3840, 4));
  assert.equal(queue.length, 3);
  assert.equal(queue[0][0], 2);
  assert.equal(shouldForwardAudio({ audioEnabled: true, audience: "audience_blocked" }), false);
  queue = flushQueue();
  assert.equal(queue.length, 0);
  assert.equal(shouldForwardAudio({ audioEnabled: true, audience: "owner_present" }), false);
  assert.equal(
    shouldForwardAudio({
      audioEnabled: true,
      audience: "owner_present",
      connectionReady: true,
      botChannelId: "c1",
      configuredChannelId: "c1",
    }),
    true,
  );
});
