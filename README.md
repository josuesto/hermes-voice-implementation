# Hermes Voice Implementation

Hermes Voice Implementation is a planned free and open-source, Windows-first bridge for using the **real Codex desktop Voice session** remotely from a phone browser. A user asks Hermes—usually through Telegram—to start a new Codex task or resume an existing one on their own awake, unlocked PC. Hermes then starts Codex Voice and returns a private browser link for two-way microphone/Codex audio over WebRTC.

The browser is the first release transport. A post-v1 optional Discord adapter is now on the roadmap: Hermes would start or stop the same Codex Voice session, and a user-owned bot would join one authorized Discord voice channel to carry audio without a web page. Discord does not gate the browser release and will reuse the same task, Voice, audio, and cleanup core.

> [!WARNING]
> **Planning and feasibility only. There is no working product release or production code yet.** CP-002, CP-003, CP-004, CP-010, CP-011, and CP-012 are Complete. CP-013 is In progress: paginated existing-task resume is unavailable under the tested safe interfaces, and its synthetically accepted fresh-task route awaits explicit live approval. CP-020, CP-030, and CP-040 are Ready. Phase Zero has not passed, and production scaffolding remains blocked.

## Intended flow

1. The user's Windows PC is awake, unlocked, and signed in to Codex; Hermes is available on that PC or another user-controlled host.
2. The user messages Hermes to start a new Codex task or resume an existing one.
3. A local companion deterministically opens the correct Codex desktop task and starts the real Voice mode.
4. After Voice is verified ready, Hermes sends the current provider-assigned private link.
5. A compatible phone browser sends microphone input and receives only Codex audio through WebRTC.
6. Ending the remote voice session stops the bridge and Voice mode while preserving the underlying Codex task.

## Core constraints

- This is not a replacement voice model, remote desktop, or centrally hosted service.
- Users own and control their Cloudflare or other provider resources; no custom domain is required.
- The bridge must never intentionally record audio or add transcripts.
- It must capture only Codex audio and must not silently fall back to system audio or the PC's physical microphone.
- Task selection, authentication, pairing, teardown, and recovery must fail closed.
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

The project is working through gated planning and feasibility checkpoints. CP-002 (target hardware and software inventory), CP-003 (privacy and threat boundaries), CP-004 (feasibility workspace and evidence harness), CP-010 (Codex surface discovery), CP-011 (deterministic Codex launch and session control), and CP-012 (recent-task enumeration and stable identity) are Complete. CP-011 established packaged activation for reliable cold launch and already-open reuse on an active, unlocked, same-owner Windows session. CP-012 established privacy-reduced enumeration through three stable App Server `thread/list` calls without opening or mutating a task.

CP-013 Stage A and its existing-task route discovery are accepted. The tested task uses paginated history, which the current App Server can list and summary-read but not resume; bounded desktop UI Automation exposed no unique stable-ID task-selection element. The project therefore rejects title-only fallback and treats existing paginated-task resume as unsupported. The redesigned fresh-task route passed its private 126-case synthetic harness and permits only collision-checked owned disposable names plus `SelectionItemPattern.Select`; live creation remains explicitly approval-gated. CP-020, CP-030, and CP-040 remain Ready under their prepared implementation plans. Other later dependents remain Pending, and CP-044 still waits on CP-041. There is still no working product release or production code. This public repository is documentation-only and does **not** satisfy CP-100 or authorize product scaffolding; those remain blocked until the Phase Zero feasibility gate passes.

- [CP-003 implementation plan](docs/checkpoints/cp-003-privacy-threat-data-flow-implementation-plan.md)
- [CP-004 implementation plan](docs/checkpoints/cp-004-feasibility-workspace-evidence-harness-implementation-plan.md)
- [CP-010 implementation plan](docs/checkpoints/cp-010-codex-surface-discovery-implementation-plan.md)
- [CP-011 implementation plan](docs/checkpoints/cp-011-deterministic-codex-launch-session-control-implementation-plan.md)
- [CP-012 implementation plan](docs/checkpoints/cp-012-recent-task-enumeration-implementation-plan.md)
- [CP-013 implementation plan](docs/checkpoints/cp-013-exact-task-control-implementation-plan.md)
- [CP-020 implementation plan](docs/checkpoints/cp-020-virtual-microphone-inventory-implementation-plan.md)
- [CP-030 implementation plan](docs/checkpoints/cp-030-mobile-capability-probe-implementation-plan.md)
- [CP-040 implementation plan](docs/checkpoints/cp-040-provider-contract-implementation-plan.md)

See the [detailed product and build plan](docs/plan.md) and [checkpoint map](docs/checkpoint-map.md).

The optional transport boundary is recorded in [ADR 0002](docs/adr/0002-browser-first-optional-discord-voice-transport.md).

## Important compatibility warning

The design automates an unofficial Codex desktop path. Desktop UI, process, package, audio, or protocol changes may break it without notice. Feasibility and supported-version claims must be proven with reproducible evidence before any release is presented as working.

## License

MIT. See [LICENSE](LICENSE).
