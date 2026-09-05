# MVP-D01: Direct Discord audio for Codex Voice

Status: implementation handoff ready; code and live acceptance pending.
Decision date: 2026-09-04.

> [!IMPORTANT] Mandatory workflow
> Codex plans and reviews. Grok 4.6 in Cursor implements this bounded slice. One short risk-based review follows, then an owner-configured live call. Codex commits and pushes accepted public-safe work and updates the project note. Do not revive the legacy feasibility checklist or describe fake tests as live audio proof.

## Outcome

The owner says "Hermes, summon Codex" through their existing Hermes conversation. Hermes opens a new or requested existing Codex task, asks for model and effort, starts actual Codex Voice, verifies both choices again, and connects the user's own bot to one private Discord guild voice channel. The owner talks from Discord on their phone and hears the real Codex replies there. "Hermes, dismiss Codex" ends Voice and the bot connection, preserving the task and its work.

These phrases are skill aliases, not renamed tools or new Discord slash commands. Keep `codex_voice_start`, `codex_voice_confirm`, `codex_voice_status`, and `codex_voice_stop`. Add `transport="discord"` alongside existing transports. No transcription, speech-to-text prompting, TTS, substitute model, browser page, public listener, or Cloudflare route belongs to this slice.

## Scope and retained behavior

- One awake, unlocked Windows PC with same-host Hermes, signed-in Codex, and VB-CABLE already configured. No new driver installation.
- One user-owned bot, one configured guild/channel, and one configured human speaker. This is a guild voice channel, not a DM/group call or a self-bot.
- New/current task modes keep the existing Hermes app-scoped computer-use flow, including recent visible names, ambiguous-choice questions, and model/effort confirmation on every call. No App Server resume or CP-013 changes.
- One audio transport owns the session. Switching during `starting` or `ready` refuses without disrupting the existing session. Discord never starts the physical microphone router or browser server.
- Joining/leaving the channel is distinct from ending Codex work. The owner can leave briefly and rejoin the existing session without asking Hermes to restart. While absent, forward neither direction and discard queued speech. Never replay unattended replies on return.
- Hermes turn completion or incomplete model/effort confirmation does not stop the session. An explicit owner stop ends Voice through computer use and releases the transport. Authorization loss or broken media closes only owned media resources, reports failure, and preserves the Codex task; it does not pretend Voice was stopped.

## Small implementation design

### Discord sidecar

Use a local Node sidecar owned by the Python companion with `discord.js` and `@discordjs/voice`. Registry metadata checked on 2026-09-04: `discord.js` 14.27.0 and `@discordjs/voice` 0.19.2; the latter requires Node >=22.12.0 and declares `@snazzah/davey` ^0.1.9 for DAVE. Pin direct versions and commit the lockfile. Use one supported Opus codec dependency. Check installed versions and DAVE initialization; do not implement encryption or silently disable it. The development/main documentation has a different Node requirement, so use the pinned release's contract.

Request only the gateway intents and channel permissions needed for guild voice membership, receive, and playback. No Administrator, message-content intent, text chat listener, public commands, or generic bot features. Receive must not be disabled by joining self-deafened. Refuse missing permissions with a bounded error.

The companion owns the sidecar `Popen` handle. Use private anonymous stdin/stdout pipes with a small length-prefixed message format that separates bounded control messages from binary PCM. Document the format; reject malformed or oversized frames and handle partial reads. No network IPC endpoint or JSON/base64 audio. Send bootstrap configuration over the private pipe, never command arguments. Do not print bootstrap, raw exceptions, tokens, Discord payloads, or audio.

### Two-way media

Incoming path: authorized Discord user Opus -> PCM -> existing Windows VB-CABLE playback sink -> Codex's configured `CABLE Output` microphone.

Outgoing path: existing unique-current-session Codex process-tree capture -> PCM -> Discord Opus playback -> owner.

Use 48 kHz, stereo, signed 16-bit little-endian PCM at the sidecar boundary. A 20 ms packet is 960 samples per channel, 3,840 bytes. Normalize formats explicitly; a moving receive meter alone is not evidence the sink wrote the right bytes. Pace outgoing frames, bound queues, and drop stale frames rather than build seconds of delay. Decode only the authorized speaker; never subscribe to the bot's own output.

Reuse `ProcessLoopbackSource` and the VB-CABLE sink logic in `companion/browser_call/server.py`. Their current module imports browser dependencies, and `CableAudioSink.consume` is coupled to a WebRTC track. Extract only the hardware/process primitives needed into a transport-neutral module, add a PCM write entry point, and preserve browser-facing imports/behavior. Keep blocking device/pipe writes off control/event-loop threads. Retain the native helper's timeout and exact-child cleanup. Do not duplicate the C# helper or introduce system-output capture as a fallback.

Discord connection can prepare during `starting`, but both audio directions remain gated until `codex_voice_confirm` verifies Voice and the post-start model/effort choices and the transport has connected successfully. An alive process is not a connected voice channel. If confirmation remains incomplete, report that state and keep the owned connection available without exposing audio.

Stop, pipe EOF, child exit, or cancellation must unblock I/O and release the sink, decoder/player, subscriptions, and owned native helper. Cooperatively stop first, with a bounded exact-child termination fallback only for a child created and still held by this session. No process-name kills, persisted-PID kills, task deletion, or window close.

### Owner configuration and privacy

Setup documentation requests a bot token, guild ID, channel ID, and owner Discord user ID, but the owner enters secrets locally, never in Hermes, Cursor, Telegram, or this chat. For this development slice, a private process environment token is acceptable; never persist it in the repository or pass it in command arguments. User IDs and channel IDs are private local configuration, excluded from public reports. Packaged credential-store setup remains later work.

Require one private channel whose audience is the owner and this bot. Receiving only the owner's mic does not prevent others from hearing the bot: if another participant appears, pause both directions, flush queued speech, and report `audience_blocked` until the channel is safe again. Do not change channel permissions automatically. The bot visibly identifies itself as the Codex audio bridge. No audio files, extra transcripts, text messages, raw account identifiers, or task titles are logged.

### Minimal status

Retain lifecycle `inactive/starting/ready/stopping/failed`. Add bounded Discord-only fields for connection, owner presence/audience safety, incoming audio, CABLE writes, and outgoing audio. Specify the enums in code and docs, with no channel URL, token, name, or ID in tool results. Derive activity from recent successful reads/writes using a monotonic window, not stream-open or a historical nonzero peak. Silence is valid. Distinguish `waiting_for_owner`, `audience_blocked`, and transport failure from audible end-to-end success.

## Expected files

- New `companion/discord_voice/` containing the Python transport wrapper, Node package/lockfile, sidecar, setup notes, and focused tests.
- Small shared audio extraction under `companion/`; update `companion/browser_call/server.py` and its existing tests only as required to preserve behavior.
- `companion/codex_control.py` and its focused tests for the third transport, ownership, confirm gating, and cleanup.
- `plugin/hermes_voice/{tools.py,__init__.py,plugin.yaml,SKILL.md}` and canonical `skills/hermes_voice/SKILL.md` for the new transport and natural-language aliases. Keep both skill copies consistent.
- Update this document with actual setup/test commands. Private worker report: `work/mvp-d01/worker-report.md`, ignored by Git.

Do not rewrite the frontend, full legacy plans, or native capture engine. Only change adjacent files when required by the above integration and explain why in the report.

## Verification and acceptance

Run the three existing Python suites once in the Hermes Python runtime, plus focused new Python/Node tests. Cover owner-only receive and self-audio exclusion; audience/absence gating and stale-buffer discard; confirmation and transport conflict; known PCM delivery in each direction with fake devices; malformed pipe/child exit; explicit stop cleanup; and bounded status that expires back to silent. Include a DAVE/Opus dependency-load check without logging into Discord. No repeated synthetic evidence program.

Worker implements and tests, then stops for Codex review. No live Discord login/join, plugin install/enable, gateway restart, Codex operation, provider change, driver install, or publishing during that worker pass. Report exact changed files, commands/results, and any remaining blocker. Do not generate dozens of approval packets.

After review and private owner setup, perform one live five-minute phone call started through Hermes. Verify intelligible speech both ways, Discord mute, a brief leave/rejoin without replay, persistence across a Hermes turn, and explicit Hermes stop that leaves Codex work intact. If a direction fails, inspect only its last successful stage and fix that boundary. Never substitute transcription to make the test appear successful. One call proves the slice; five consecutive successful calls remain the packaging acceptance target.

## Primary references

- [Discord voice protocol](https://docs.discord.com/developers/topics/voice-connections). Current DAVE requirements and transport rules.
- [Discord.js Voice documentation](https://discord.js.org/docs/packages/voice/stable). Maintained send/receive library; its documentation warns that Discord does not document audio receive as a stable contract. A live receive test is essential.
- [Published voice package](https://www.npmjs.com/package/@discordjs/voice/v/0.19.2) and [published Discord client](https://www.npmjs.com/package/discord.js/v/14.27.0). Version and runtime baseline, checked through the registry.

Discord handles the phone client and its network transport, not the Windows mic routing. This slice removes browser-specific work while still proving the real VB-CABLE and process-capture path.
