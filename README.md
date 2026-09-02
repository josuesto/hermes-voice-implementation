# Hermes Voice Implementation

Hermes Voice Implementation is a planned free and open-source, Windows-first bridge for using the **real Codex desktop Voice session** remotely from a phone browser. A user asks Hermes—usually through Telegram—to start a new Codex task or resume an existing one on their own awake, unlocked PC. Hermes then starts Codex Voice and returns a private browser link for two-way microphone/Codex audio over WebRTC.

The browser is the first release transport. A post-v1 optional Discord adapter is now on the roadmap: Hermes would start or stop the same Codex Voice session, and a user-owned bot would join one authorized Discord voice channel to carry audio without a web page. Discord does not gate the browser release and will reuse the same task, Voice, audio, and cleanup core.

> [!WARNING]
> **Development is intentionally paused as of September 2, 2026; there is no packaged release yet.** A working same-host prototype exists. MVP-01 proves Windows playback and the installed VB-CABLE route with 18 passing tests and no saved audio. MVP-02 is accepted, and plugin version 0.5.0 is installed and enabled on the reference PC: a real Telegram request successfully selected the task, asked for model and effort, started Voice, and carried continuously routed Blue Snowball audio into Codex. MVP-03 has a persistent local WebRTC host, microphone selection and activity feedback, bounded browser/CABLE diagnostics, and a working Windows process-tree capture helper that returns only Codex audio. The remaining MVP-03 gate is one successful live browser-to-Codex-to-browser call and the phone-safe HTTPS/auth layer. See the [pause handoff](docs/pause-handoff-2026-09-02.md) before resuming.

## Intended flow

1. The user's Windows PC is awake, unlocked, and signed in to Codex; Hermes is available on that PC or another user-controlled host.
2. The user messages Hermes to start a new Codex task or resume an existing one.
3. Hermes asks which available model and reasoning effort to use, applies both to the selected task, and a local companion starts the real Voice mode.
4. Hermes re-checks both settings after Voice startup, because Voice may change them, and sends the private link only after the complete session is verified ready.
5. A compatible phone browser sends microphone input and receives only Codex audio through WebRTC.
6. Ending the remote voice session stops the bridge and Voice mode while preserving the underlying Codex task.

## Core constraints

- This is not a replacement voice model, remote desktop, or centrally hosted service.
- Users own and control their Cloudflare or other provider resources; no custom domain is required.
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
- **Embedded phone page:** provides a minimal browser call interface over WebRTC.
- **Optional Discord adapter (post-v1):** lets a user-owned bot expose the same session in one authorized Discord voice call under Hermes control.
- **User-owned networking:** serves the page and signaling through provider-owned HTTPS/STUN/TURN resources.

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

The optional transport boundary is recorded in [ADR 0002](docs/adr/0002-browser-first-optional-discord-voice-transport.md).

## Important compatibility warning

The design automates an unofficial Codex desktop path. Desktop UI, process, package, audio, or protocol changes may break it without notice. Feasibility and supported-version claims must be proven with reproducible evidence before any release is presented as working.

## License

MIT. See [LICENSE](LICENSE).
