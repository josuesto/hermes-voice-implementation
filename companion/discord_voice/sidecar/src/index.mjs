import { PassThrough } from "node:stream";
import { createRequire } from "node:module";
import {
  createAudioPlayer,
  createAudioResource,
  entersState,
  generateDependencyReport,
  joinVoiceChannel,
  NoSubscriberBehavior,
  StreamType,
  VoiceConnectionStatus,
  EndBehaviorType,
} from "@discordjs/voice";
import {
  ChannelType,
  Client,
  GatewayIntentBits,
  PermissionFlagsBits,
} from "discord.js";
import { createSidecarSession, PCM_PACKET_BYTES } from "./runtime.mjs";
import {
  decodeControl,
  encodeControl,
  encodeFrame,
  FrameDecoder,
  ProtocolError,
  TYPE_CONTROL,
  TYPE_PCM_IN,
  TYPE_PCM_OUT,
} from "./protocol.mjs";

const require = createRequire(import.meta.url);
const OpusScript = require("opusscript");
const CONNECT_TIMEOUT_MS = 12000;
const decoder = new FrameDecoder();
const opus = new OpusScript(48000, 2, OpusScript.Application.AUDIO);

let client = null;
let stdoutNeedDrain = false;

function writeStdout(buffer) {
  if (!process.stdout.writable || stdoutNeedDrain) {
    return false;
  }
  const ok = process.stdout.write(buffer);
  if (!ok) {
    stdoutNeedDrain = true;
  }
  return ok;
}

function currentMemberIds(channel) {
  return [...channel.members.keys()].map(String);
}

const session = createSidecarSession({
  readyStatus: VoiceConnectionStatus.Ready,
  sendState({ connection, audience, error }) {
    const message = {
      op: "state",
      connection,
      audience,
    };
    if (error) {
      message.error = error;
    }
    writeStdout(encodeControl(message));
  },
  sendError(code) {
    writeStdout(encodeControl({ op: "error", code }));
  },
  createPlayer() {
    return createAudioPlayer({ behaviors: { noSubscriber: NoSubscriberBehavior.Pause } });
  },
  createResource(stream) {
    return createAudioResource(stream, { inputType: StreamType.Raw });
  },
  createPlaybackStream() {
    return new PassThrough({ highWaterMark: PCM_PACKET_BYTES * 3 });
  },
  subscribeOwnerReceive(connection, ownerId) {
    return connection.receiver.subscribe(ownerId, {
      end: { behavior: EndBehaviorType.Manual },
    });
  },
  onOwnerPacket(packet) {
    try {
      const pcm = opus.decode(packet);
      if (pcm.length === PCM_PACKET_BYTES) {
        writeStdout(encodeFrame(TYPE_PCM_IN, pcm));
      }
    } catch {
      return;
    }
  },
  getConfiguredMemberIds() {
    const guild = client?.guilds?.cache?.get(session.state.guildId);
    const channel = guild?.channels?.cache?.get(session.state.channelId);
    return channel ? currentMemberIds(channel) : [];
  },
  async joinChannel() {
    const guild = await client.guilds.fetch(session.state.guildId);
    const channel = await guild.channels.fetch(session.state.channelId);
    if (!channel || channel.type !== ChannelType.GuildVoice) {
      session.state.fatal = true;
      writeStdout(encodeControl({ op: "error", code: "discord_permission_missing" }));
      session.state.connectionState = "failed";
      session.sendState("discord_permission_missing");
      process.exitCode = 1;
      throw new Error("discord_permission_missing");
    }
    const me = guild.members.me ?? (await guild.members.fetchMe());
    const permissions = channel.permissionsFor(me);
    const needed = [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.Connect, PermissionFlagsBits.Speak];
    if (!permissions || !permissions.has(needed)) {
      session.state.fatal = true;
      writeStdout(encodeControl({ op: "error", code: "discord_permission_missing" }));
      session.state.connectionState = "failed";
      session.sendState("discord_permission_missing");
      process.exitCode = 1;
      throw new Error("discord_permission_missing");
    }
    const connection = joinVoiceChannel({
      channelId: session.state.channelId,
      guildId: session.state.guildId,
      adapterCreator: guild.voiceAdapterCreator,
      selfDeaf: false,
      selfMute: false,
    });
    await entersState(connection, VoiceConnectionStatus.Ready, CONNECT_TIMEOUT_MS);
    return { connection, memberIds: currentMemberIds(channel) };
  },
});

function onVoiceStateUpdate(before, after) {
  if (session.state.fatal || session.state.shuttingDown) {
    return;
  }
  const botId = session.state.botId;
  const ownerId = session.state.ownerId;
  const channelId = session.state.channelId;
  const botTouched = String(after.id) === botId || String(before.id) === botId;
  const configuredTouched = before.channelId === channelId || after.channelId === channelId;
  const ownerTouched = String(after.id) === ownerId || String(before.id) === ownerId;
  if (!botTouched && !configuredTouched && !ownerTouched) {
    return;
  }
  const guild = after.guild ?? before.guild;
  const channel = guild?.channels?.cache?.get(channelId);
  void session.applyLiveVoiceEvent(channel ? currentMemberIds(channel) : []);
}

async function assertDaveAndOpus() {
  await import("@snazzah/davey");
  await import("opusscript");
  generateDependencyReport();
}

async function startClient(bootstrap) {
  session.state.ownerId = String(bootstrap.owner_id || "");
  session.state.guildId = String(bootstrap.guild_id || "");
  session.state.channelId = String(bootstrap.channel_id || "");
  const token = String(bootstrap.token || "");
  if (!session.state.ownerId || !session.state.guildId || !session.state.channelId || !token) {
    writeStdout(encodeControl({ op: "error", code: "discord_start_failed" }));
    process.exitCode = 1;
    return;
  }
  await assertDaveAndOpus();
  client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildVoiceStates],
  });
  client.once("ready", async () => {
    session.state.botId = client.user.id;
    try {
      await client.user.setPresence({
        activities: [{ name: "Codex audio bridge" }],
      });
    } catch {
      /* identity is set in the developer portal; presence is best-effort */
    }
    client.on("voiceStateUpdate", onVoiceStateUpdate);
    try {
      const memberIds = await session.joinConfiguredChannel();
      await session.applyLiveVoiceEvent(memberIds);
    } catch {
      session.state.fatal = true;
      session.state.connectionState = "failed";
      writeStdout(encodeControl({ op: "error", code: "discord_start_failed" }));
      session.sendState("discord_start_failed");
      process.exitCode = 1;
    }
  });
  await client.login(token);
}

function handleControl(payload) {
  const message = decodeControl(payload);
  if (message.op === "bootstrap") {
    startClient(message).catch(() => {
      writeStdout(encodeControl({ op: "error", code: "discord_start_failed" }));
      process.exitCode = 1;
    });
    return;
  }
  if (message.op === "gate") {
    session.setAudioEnabled(message.audio === true);
    return;
  }
  if (message.op === "flush") {
    session.flushAndMaybeRestore();
    return;
  }
  if (message.op === "stop") {
    shutdown();
  }
}

function shutdown() {
  if (session.state.shuttingDown) {
    return;
  }
  session.state.shuttingDown = true;
  session.pauseMedia();
  if (session.state.voiceConnection) {
    session.state.voiceConnection.destroy();
    session.state.voiceConnection = null;
  }
  if (client) {
    client.destroy();
    client = null;
  }
  process.exit(0);
}

if (process.argv.includes("--check-deps")) {
  assertDaveAndOpus()
    .then(() => {
      process.exit(0);
    })
    .catch(() => {
      process.exit(1);
    });
} else {
  process.stdout.on("drain", () => {
    stdoutNeedDrain = false;
  });

  process.stdin.on("data", (chunk) => {
    try {
      for (const frame of decoder.push(chunk)) {
        if (frame.type === TYPE_CONTROL) {
          handleControl(frame.payload);
        } else if (frame.type === TYPE_PCM_OUT) {
          if (frame.payload.length === PCM_PACKET_BYTES) {
            session.pushOutbound(frame.payload);
          }
        }
      }
    } catch (error) {
      if (error instanceof ProtocolError) {
        writeStdout(encodeControl({ op: "error", code: "discord_start_failed" }));
        process.exitCode = 1;
        shutdown();
        return;
      }
      writeStdout(encodeControl({ op: "error", code: "discord_start_failed" }));
      process.exitCode = 1;
      shutdown();
    }
  });

  process.stdin.on("end", () => {
    shutdown();
  });

  process.stdin.on("error", () => {
    shutdown();
  });

  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}
