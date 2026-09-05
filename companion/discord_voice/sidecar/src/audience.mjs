export const QUEUE_LIMIT_FRAMES = 3;
export const PCM_PACKET_BYTES = 3840;

export function classifyAudience({ memberIds, ownerId, botId }) {
  const ids = Array.isArray(memberIds) ? memberIds.map(String) : [];
  const owner = String(ownerId);
  const bot = String(botId);
  const others = ids.filter((id) => id !== owner && id !== bot);
  if (others.length > 0) {
    return "audience_blocked";
  }
  if (!ids.includes(owner) || !ids.includes(bot)) {
    return "waiting_for_owner";
  }
  return "owner_present";
}

export function shouldSubscribe({ userId, ownerId, botId }) {
  return String(userId) === String(ownerId) && String(userId) !== String(botId);
}

export function shouldForwardAudio({
  audioEnabled,
  audience,
  connectionReady = false,
  botChannelId = null,
  configuredChannelId = null,
}) {
  return (
    audioEnabled === true &&
    audience === "owner_present" &&
    connectionReady === true &&
    botChannelId != null &&
    configuredChannelId != null &&
    String(botChannelId) === String(configuredChannelId)
  );
}

export function applyVoiceEvent({
  audioEnabled,
  configuredChannelId,
  ownerId,
  botId,
  botChannelId,
  connectionReady,
  configuredMemberIds,
  previousConnectionReady = false,
}) {
  const botOnConfigured =
    botChannelId != null &&
    configuredChannelId != null &&
    String(botChannelId) === String(configuredChannelId);
  const ready = connectionReady === true && botOnConfigured;
  const members = Array.isArray(configuredMemberIds) ? configuredMemberIds : [];
  const classified = classifyAudience({
    memberIds: members,
    ownerId,
    botId,
  });
  const audience = botOnConfigured
    ? classified
    : classified === "audience_blocked"
      ? "audience_blocked"
      : "waiting_for_owner";
  const forwarding = shouldForwardAudio({
    audioEnabled,
    audience,
    connectionReady: ready,
    botChannelId,
    configuredChannelId,
  });
  const movedOffConfigured =
    botChannelId != null &&
    configuredChannelId != null &&
    String(botChannelId) !== String(configuredChannelId);
  const disconnected = botChannelId == null || connectionReady !== true;
  return {
    audience,
    connection: ready ? "connected" : "connecting",
    forwarding,
    shouldPause: !forwarding,
    shouldAbandonMovedChannel: movedOffConfigured,
    shouldReconnectToConfigured: movedOffConfigured || (previousConnectionReady === true && disconnected),
  };
}

export function enqueueFrame(queue, frame, limit = QUEUE_LIMIT_FRAMES) {
  const next = Array.isArray(queue) ? queue.slice() : [];
  next.push(frame);
  while (next.length > limit) {
    next.shift();
  }
  return next;
}

export function flushQueue() {
  return [];
}

export function writeWithBackpressure(stream, frame) {
  if (!stream || !stream.writable || stream.writableNeedDrain) {
    return { accepted: false, waitDrain: true };
  }
  const ok = stream.write(frame);
  return { accepted: true, waitDrain: !ok };
}

export function flushBoundedQueue(queue, stream) {
  const next = Array.isArray(queue) ? queue.slice() : [];
  while (next.length > 0) {
    if (!stream || !stream.writable || stream.writableNeedDrain) {
      break;
    }
    const frame = next.shift();
    const ok = stream.write(frame);
    if (!ok) {
      break;
    }
  }
  return next;
}
