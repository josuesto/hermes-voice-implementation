# Discord transport extras

Optional. Physical-microphone and browser transports load without Node or Discord credentials.

This sidecar uses `discord.js` 14.27.0 and `@discordjs/voice` 0.19.2. Node.js 22.12.0 or newer is required. DAVE comes from the voice package's `@snazzah/davey` dependency. Opus uses `opusscript`, a supported codec that does not require a native compiler on this machine. Do not disable encryption.

## Install sidecar dependencies

From the implementation tree:

```
npm ci --prefix companion/discord_voice/sidecar
```

Then:

```
node companion/discord_voice/sidecar/src/index.mjs --check-deps
```

That load check must not log into Discord.

## Owner-only local secrets

Create a user-owned Discord application and bot. In the developer portal, set the visible bot name to `Codex audio bridge`. On the Bot page, enable the Guilds and Guild Voice States gateway intents. Those are ordinary gateway intents, not privileged portal toggles. Leave Message Content disabled. Do not grant Administrator.

Invite the bot to one private guild with View Channel, Connect, and Speak on one private voice channel. Do not join the bot self-deafened.

Set these in the same process environment that runs Hermes. Never put them in Git, Telegram, Cursor, or this chat:

```
HERMES_VOICE_DISCORD_TOKEN
HERMES_VOICE_DISCORD_GUILD_ID
HERMES_VOICE_DISCORD_CHANNEL_ID
HERMES_VOICE_DISCORD_OWNER_ID
```

The companion reads those values and sends bootstrap configuration over a private anonymous pipe. The token never appears in command arguments.

## Focused tests

```
node --test companion/discord_voice/sidecar/tests/*.test.mjs
python -m unittest companion.discord_voice.tests.test_protocol companion.discord_voice.tests.test_audio_io companion.discord_voice.tests.test_transport
```

Use the Hermes Python interpreter for the existing suites listed in `docs/mvp-d01-discord-voice.md`.

## Pipe format

stdin/stdout frames are `uint32le length`, then one type byte, then payload. Type `1` is UTF-8 JSON control. Type `2` is inbound PCM (Discord owner to Python). Type `3` is outbound PCM (Python to Discord). PCM is 48 kHz stereo s16le. A 20 ms packet is 3,840 bytes. Maximum frame body is 16,384 bytes. Malformed or oversized frames fail closed.

## Live call is later

A library import and fake PCM delivery are not live Discord receive or Codex audibility proof. After private owner setup, the live five-minute call is a separate acceptance step.
