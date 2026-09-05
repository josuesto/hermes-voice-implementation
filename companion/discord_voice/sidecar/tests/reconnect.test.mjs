import test from "node:test";
import assert from "node:assert/strict";
import { PassThrough } from "node:stream";
import { createSidecarSession, PCM_PACKET_BYTES } from "../src/runtime.mjs";

const CONFIGURED = "channel-configured";
const ELSEWHERE = "channel-elsewhere";
const FRAME = Buffer.alloc(PCM_PACKET_BYTES, 7);

function fakeConnection({ channelId, status = "ready" }) {
  const listeners = [];
  const subscribed = [];
  const receive = [];
  const connection = {
    joinConfig: { channelId },
    state: { status },
    destroyed: false,
    subscribed,
    receive,
    subscribe(player) {
      subscribed.push(player);
      return { player };
    },
    receiver: {
      subscribe(userId, options) {
        const stream = new PassThrough();
        receive.push({ userId, options, stream });
        return stream;
      },
    },
    on(event, fn) {
      listeners.push({ event, fn });
    },
    emit(event, ...args) {
      for (const listener of listeners) {
        if (listener.event === event) {
          listener.fn(...args);
        }
      }
    },
    destroy() {
      this.destroyed = true;
      this.state = { status: "destroyed" };
      this.joinConfig = { channelId: null };
      this.emit("stateChange", { status: "ready" }, this.state);
    },
  };
  return connection;
}

function fakePlayer() {
  return {
    stopped: 0,
    played: [],
    stop() {
      this.stopped += 1;
    },
    play(resource) {
      this.played.push(resource);
    },
  };
}

function createHarness({ memberIds, joinImpl }) {
  const states = [];
  const errors = [];
  let nextConnection = null;
  let members = memberIds.slice();
  const session = createSidecarSession({
    sendState(snapshot) {
      states.push({ ...snapshot });
    },
    sendError(code) {
      errors.push(code);
    },
    createPlayer: fakePlayer,
    createResource(stream) {
      return { stream };
    },
    createPlaybackStream() {
      return new PassThrough({ highWaterMark: PCM_PACKET_BYTES * 3 });
    },
    subscribeOwnerReceive(connection, ownerId) {
      return connection.receiver.subscribe(ownerId, { end: { behavior: "manual" } });
    },
    getConfiguredMemberIds() {
      return members.slice();
    },
    async joinChannel() {
      if (joinImpl) {
        return joinImpl();
      }
      const connection = nextConnection ?? fakeConnection({ channelId: CONFIGURED });
      nextConnection = null;
      return { connection, memberIds: members.slice() };
    },
  });
  session.state.ownerId = "owner";
  session.state.botId = "bot";
  session.state.guildId = "guild";
  session.state.channelId = CONFIGURED;
  return {
    session,
    states,
    errors,
    setMembers(ids) {
      members = ids.slice();
    },
    queueJoin(connection) {
      nextConnection = connection;
    },
  };
}

test("configured-channel Ready rejoin restores media on the new connection without replay", async () => {
  const first = fakeConnection({ channelId: CONFIGURED });
  const replacement = fakeConnection({ channelId: CONFIGURED });
  const harness = createHarness({ memberIds: ["owner", "bot"] });
  harness.queueJoin(first);
  harness.session.state.audioEnabled = true;

  const initialMembers = await harness.session.joinConfiguredChannel();
  await harness.session.applyLiveVoiceEvent(initialMembers);

  assert.equal(harness.session.state.connectionState, "connected");
  assert.equal(harness.session.state.audience, "owner_present");
  assert.ok(harness.session.state.pcmStream);
  assert.equal(first.receive.length, 1);
  assert.equal(first.subscribed.length, 1);
  const player = first.subscribed[0];
  harness.session.state.outboundQueue = [FRAME, FRAME];
  assert.equal(harness.session.state.outboundQueue.length, 2);

  first.joinConfig.channelId = ELSEWHERE;
  harness.queueJoin(replacement);
  await harness.session.applyLiveVoiceEvent(["owner", "bot"]);

  assert.equal(harness.session.state.reconnecting, false);
  assert.equal(harness.session.state.connectionState, "connected");
  assert.equal(harness.session.state.audience, "owner_present");
  assert.equal(harness.session.state.voiceConnection, replacement);
  assert.equal(first.destroyed, true);
  assert.ok(harness.session.state.pcmStream);
  assert.equal(harness.session.state.outboundQueue.length, 0);
  assert.equal(replacement.subscribed.length, 1);
  assert.equal(replacement.subscribed[0], player);
  assert.equal(first.subscribed.length, 1);
  assert.equal(replacement.receive.length, 1);
  assert.equal(replacement.receive[0].userId, "owner");
  assert.ok(harness.session.state.receiveStream);
  assert.notEqual(harness.session.state.receiveStream, first.receive[0].stream);

  harness.setMembers(["owner", "bot", "extra"]);
  await harness.session.applyLiveVoiceEvent(["owner", "bot", "extra"]);
  assert.equal(harness.session.state.audience, "audience_blocked");
  assert.equal(harness.session.state.pcmStream, null);
  assert.equal(harness.session.state.receiveStream, null);
  assert.equal(harness.session.state.outboundQueue.length, 0);
  assert.equal(harness.session.mediaAuthorized(), false);

  harness.setMembers(["bot"]);
  await harness.session.applyLiveVoiceEvent(["bot"]);
  assert.equal(harness.session.state.audience, "waiting_for_owner");
  assert.equal(harness.session.state.pcmStream, null);
  assert.equal(harness.session.state.receiveStream, null);
  assert.equal(harness.session.mediaAuthorized(), false);
});
