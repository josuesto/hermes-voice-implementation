import { PassThrough } from "node:stream";
import {
  applyVoiceEvent,
  enqueueFrame,
  flushBoundedQueue,
  flushQueue,
  PCM_PACKET_BYTES,
  shouldForwardAudio,
  shouldSubscribe,
} from "./audience.mjs";

export { PCM_PACKET_BYTES };

const READY = "ready";

export function createSidecarSession(hooks) {
  const readyStatus = hooks.readyStatus ?? READY;
  const state = {
    audioEnabled: false,
    audience: "waiting_for_owner",
    connectionState: "idle",
    outboundQueue: [],
    pcmStream: null,
    player: null,
    voiceConnection: null,
    receiveStream: null,
    ownerId: "",
    botId: "",
    guildId: "",
    channelId: "",
    shuttingDown: false,
    reconnecting: false,
    fatal: false,
    lastReady: false,
  };

  function sendState(errorCode) {
    hooks.sendState?.({
      connection: state.connectionState,
      audience: state.audience,
      error: errorCode,
    });
  }

  function sendError(code) {
    hooks.sendError?.(code);
  }

  function currentBotChannelId() {
    return state.voiceConnection?.joinConfig?.channelId ?? null;
  }

  function currentConnectionReady() {
    return state.voiceConnection?.state?.status === readyStatus;
  }

  function mediaAuthorized() {
    return shouldForwardAudio({
      audioEnabled: state.audioEnabled,
      audience: state.audience,
      connectionReady: currentConnectionReady(),
      botChannelId: currentBotChannelId(),
      configuredChannelId: state.channelId,
    });
  }

  function destroyReceive() {
    if (state.receiveStream) {
      state.receiveStream.destroy();
      state.receiveStream = null;
    }
  }

  function pauseMedia() {
    destroyReceive();
    state.outboundQueue = flushQueue();
    if (state.player) {
      state.player.stop(true);
    }
    if (state.pcmStream) {
      state.pcmStream.destroy();
      state.pcmStream = null;
    }
  }

  function attachPlayer(connection) {
    if (!connection) {
      return;
    }
    if (!state.player) {
      state.player = hooks.createPlayer();
    }
    connection.subscribe(state.player);
  }

  function replacePlaybackStream() {
    state.outboundQueue = flushQueue();
    if (state.pcmStream) {
      state.pcmStream.destroy();
      state.pcmStream = null;
    }
    if (state.player) {
      state.player.stop(true);
    }
    if (!state.voiceConnection || !mediaAuthorized()) {
      return;
    }
    const stream = hooks.createPlaybackStream
      ? hooks.createPlaybackStream()
      : new PassThrough({ highWaterMark: PCM_PACKET_BYTES * 3 });
    stream.on("drain", () => {
      state.outboundQueue = flushBoundedQueue(state.outboundQueue, stream);
    });
    state.pcmStream = stream;
    const resource = hooks.createResource(stream);
    attachPlayer(state.voiceConnection);
    state.player.play(resource);
  }

  function subscribeOwner() {
    if (!state.voiceConnection || !mediaAuthorized()) {
      return;
    }
    if (!shouldSubscribe({ userId: state.ownerId, ownerId: state.ownerId, botId: state.botId })) {
      return;
    }
    if (state.receiveStream) {
      return;
    }
    const stream = hooks.subscribeOwnerReceive(state.voiceConnection, state.ownerId);
    state.receiveStream = stream;
    stream.on("data", (packet) => {
      if (!mediaAuthorized()) {
        return;
      }
      hooks.onOwnerPacket?.(packet);
    });
    stream.on("close", () => {
      if (state.receiveStream === stream) {
        state.receiveStream = null;
      }
    });
  }

  function restoreAuthorizedMedia() {
    if (!mediaAuthorized()) {
      pauseMedia();
      return;
    }
    if (!state.pcmStream) {
      replacePlaybackStream();
    } else {
      attachPlayer(state.voiceConnection);
    }
    subscribeOwner();
  }

  function configuredMemberIds() {
    return hooks.getConfiguredMemberIds?.() ?? [];
  }

  function watchConnection(connection) {
    connection.on("stateChange", (_old, next) => {
      if (next.status !== readyStatus) {
        pauseMedia();
      }
      void applyLiveVoiceEvent(configuredMemberIds());
    });
  }

  async function applyLiveVoiceEvent(memberIds) {
    if (state.fatal || state.shuttingDown) {
      return null;
    }
    if (state.reconnecting) {
      return null;
    }
    const result = applyVoiceEvent({
      audioEnabled: state.audioEnabled,
      configuredChannelId: state.channelId,
      ownerId: state.ownerId,
      botId: state.botId,
      botChannelId: currentBotChannelId(),
      connectionReady: currentConnectionReady(),
      configuredMemberIds: memberIds,
      previousConnectionReady: state.lastReady,
    });
    state.lastReady = result.connection === "connected";
    state.audience = result.audience;
    if (result.shouldPause) {
      pauseMedia();
    }
    if (result.shouldAbandonMovedChannel || result.shouldReconnectToConfigured) {
      state.connectionState = "connecting";
      sendState();
      await rejoinConfiguredIfNeeded();
      return result;
    }
    state.connectionState = result.connection;
    if (result.forwarding) {
      restoreAuthorizedMedia();
    }
    sendState();
    return result;
  }

  async function joinConfiguredChannel() {
    state.connectionState = "connecting";
    sendState();
    const joined = await hooks.joinChannel();
    state.voiceConnection = joined.connection;
    watchConnection(joined.connection);
    return joined.memberIds ?? [];
  }

  async function rejoinConfiguredIfNeeded() {
    if (state.reconnecting || state.shuttingDown || state.fatal) {
      return;
    }
    state.reconnecting = true;
    state.lastReady = false;
    pauseMedia();
    const moved = state.voiceConnection;
    state.voiceConnection = null;
    if (moved) {
      try {
        moved.destroy();
      } catch {
        /* the moved connection must not keep playing */
      }
    }
    try {
      const memberIds = await joinConfiguredChannel();
      state.reconnecting = false;
      await applyLiveVoiceEvent(memberIds);
    } catch {
      state.fatal = true;
      state.connectionState = "failed";
      sendError("discord_not_connected");
      sendState("discord_not_connected");
    } finally {
      state.reconnecting = false;
    }
  }

  function pushOutbound(pcm) {
    if (!mediaAuthorized()) {
      state.outboundQueue = flushQueue();
      return;
    }
    if (!state.pcmStream || !state.pcmStream.writable || state.pcmStream.writableNeedDrain) {
      state.outboundQueue = enqueueFrame(state.outboundQueue, pcm);
      return;
    }
    state.outboundQueue = enqueueFrame(state.outboundQueue, pcm);
    state.outboundQueue = flushBoundedQueue(state.outboundQueue, state.pcmStream);
  }

  function setAudioEnabled(enabled) {
    state.audioEnabled = enabled === true;
    if (mediaAuthorized()) {
      replacePlaybackStream();
      subscribeOwner();
    } else {
      pauseMedia();
    }
    sendState();
  }

  function flushAndMaybeRestore() {
    pauseMedia();
    if (mediaAuthorized()) {
      replacePlaybackStream();
      subscribeOwner();
    }
    sendState();
  }

  return {
    state,
    applyLiveVoiceEvent,
    rejoinConfiguredIfNeeded,
    joinConfiguredChannel,
    pauseMedia,
    replacePlaybackStream,
    subscribeOwner,
    restoreAuthorizedMedia,
    pushOutbound,
    setAudioEnabled,
    flushAndMaybeRestore,
    mediaAuthorized,
    sendState,
  };
}
