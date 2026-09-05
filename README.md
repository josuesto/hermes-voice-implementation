# Hermes Voice Implementation

Hermes Voice Implementation is a free and open-source, Windows-first project for using the **real Codex desktop Voice session** remotely. The next call endpoint is a user-owned bot in a private Discord voice channel. The user asks Hermes through Telegram to start a new Codex task or resume an existing one on their awake, unlocked PC; Hermes starts Voice and connects the bot for direct two-way audio.

The owner selected Discord first on September 4, 2026. The unfinished browser transport is preserved for later work. Discord reuses the task, Voice, VB-CABLE, and process-capture core; it does not replace Codex with speech-to-text, TTS, or a different model. No transcription is included.

> [!WARNING]
> **Discord implementation reviewed on September 4, 2026; private setup and a real call are still pending.** Plugin 0.6.0 includes the owner-only Discord transport, DAVE-capable sidecar, and shared Windows audio path. The final independent Node suite passed 15 tests; focused Discord Python passed 15 in the preceding review. No live Discord audibility or installed 0.6.0 runtime is claimed. See the [implementation review](docs/mvp-d01-implementation-review.md) and [setup notes](companion/discord_voice/SETUP.md). The parked browser remains unaccepted; its historical [pause handoff](docs/pause-handoff-2026-09-02.md) does not gate Discord work.

## Intended flow

1. The user's Windows PC is awake, unlocked, and signed in to Codex; Hermes is available on that PC or another user-controlled host.
2. The user messages Hermes to start a new Codex task or resume an existing one.
3. Hermes asks which available model and reasoning effort to use, applies both to the selected task, and a local companion starts the real Voice mode.
4. Hermes re-checks both settings after Voice startup, because Voice may change them, and confirms the configured Discord connection before enabling audio.
5. The owner joins the private Discord voice channel from their phone. The bot forwards their microphone to Codex and returns only Codex audio. A brief leave/rejoin preserves the session without replaying queued speech.
6. Ending the remote voice session stops the bridge and Voice mode while preserving the underlying Codex task.

## Core constraints

- This is not a replacement voice model, remote desktop, or centrally hosted service.
- Users own their Discord bot and PC bridge. The Discord path requires no Cloudflare deployment or custom domain; browser networking remains later work.
- The bridge must never intentionally record audio or add transcripts.
- It must capture only Codex audio and must not silently fall back to system audio or the PC's physical microphone.
- Task selection, authentication, pairing, teardown, and recovery must fail closed.
- Every Voice start explicitly confirms its model and reasoning effort; current visible choices are discovered instead of hardcoded.
- Windows is the initial target; phone support will be capability-based and evidence-driven.

## Planned architecture

- **Hermes plugin and bundled skill:** interprets owner requests and invokes deterministic local tools.
- **Windows companion:** manages lifecycle, authorization, task selection, networking, and cleanup.
- **Codex adapter:** opens or resumes the exact desktop task and controls Voice mode.
- **Audio engine:** routes phone microphone audio into Codex and captures only Codex output.
- **Discord adapter (next implementation):** lets a user-owned bot expose the same session in one authorized private voice channel under Hermes control.
- **Embedded phone page (deferred):** preserves the existing browser call implementation for later validation.
- **Browser networking (deferred):** serves the page and signaling through user-owned HTTPS/STUN/TURN resources.

## Project status

The project completed its baseline inventory, security boundaries, deterministic Codex launch, and recent-task discovery research. That work remains useful, but the active execution path is now the short [MVP roadmap](docs/mvp-roadmap.md). MVP implementation starts with a fresh task and the real Voice/audio loop.

Existing paginated-task resume through the App Server is unsupported under the tested interface, but that does not remove resume from the product. The practical MVP uses Hermes computer use to read visible recent conversation names, asks the user when selection is ambiguous, opens the confirmed conversation, and then delegates Voice/audio lifecycle to the deterministic plugin. Strong stable-ID correlation remains release hardening. The execution change is recorded in [ADR 0003](docs/adr/0003-vertical-slice-mvp-execution.md).

- [CP-003 implementation plan](docs/checkpoints/cp-003-privacy-threat-data-flow-implementation-plan.md)
- [CP-004 implementation plan](docs/checkpoints/cp-004-feasibility-workspace-evidence-harness-implementation-plan.md)
- [CP-010 implementation plan](docs/checkpoints/cp-010-codex-surface-discovery-implementation-plan.md)
- [CP-011 implementation plan](docs/checkpoints/cp-011-deterministic-codex-launch-session-control-implementation-plan.md)
- [CP-012 implementation plan](docs/checkpoints/cp-012-recent-task-enumeration-implementation-plan.md)
- [CP-013 implementation plan](docs/checkpoints/cp-013-exact-task-control-implementation-plan.md)
- [CP-020 implementation plan](docs/checkpoints/cp-020-virtual-microphone-inventory-implementation-plan.md)
- [CP-030 implementation plan](docs/checkpoints/cp-030-mobile-capability-probe-implementation-plan.md)
- [CP-040 implementation plan](docs/checkpoints/cp-040-provider-contract-implementation-plan.md)

See the active [MVP roadmap](docs/mvp-roadmap.md), the [detailed product plan](docs/plan.md), and the legacy [checkpoint map](docs/checkpoint-map.md).

The current transport decision is recorded in [ADR 0004](docs/adr/0004-discord-first-direct-audio.md), which supersedes ADR 0002's sequencing. Codex plans and reviews; Grok 4.6 in Cursor implements the next bounded slice.

## Important compatibility warning

The design automates an unofficial Codex desktop path. Desktop UI, process, package, audio, or protocol changes may break it without notice. Feasibility and supported-version claims must be proven with reproducible evidence before any release is presented as working.

## License

MIT. See [LICENSE](LICENSE).
