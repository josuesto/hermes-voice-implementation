# Hermes Voice Implementation — MVP Roadmap

Status: active execution roadmap
Decision date: 2026-09-01

This roadmap supersedes the legacy checkpoint map as the gate for the first working prototype. The detailed checkpoint material remains useful research and later hardening guidance, but it no longer blocks vertical-slice implementation.

Acceleration changes sequencing and review depth, not the agreed product behavior. The detailed plan remains the authoritative feature contract. A capability may be postponed to a later milestone for implementation reasons, but it is not removed from the product unless the owner explicitly changes the plan.

## MVP contract

- Windows only; the PC is on, awake, unlocked, signed into Windows, and already signed into Codex.
- Same-host Hermes first.
- One user and one active remote Voice session.
- New and existing Codex tasks are both part of the intended flow. Hermes infers the mode when clear and asks when ambiguous. For the practical MVP, Hermes computer use may read the visible recent-task list and select a user-confirmed title; stronger stable-ID correlation remains release hardening.
- Manual setup is acceptable, but manual runtime startup is not. Hermes must launch Codex, create or select the requested conversation, and start Voice before any end-to-end call is considered working.
- Every new or resumed Voice call requires the user to choose the currently available Codex model and reasoning effort. Hermes sets and verifies both before Voice, then re-checks and corrects any automatic change after Voice starts.
- LAN first, then user-owned Cloudflare remote access.
- Browser call first; Discord remains post-MVP.

## Safety floor

- Never request, log, or publish credentials, prompts, task contents, transcripts, or audio.
- Never delete a Codex task.
- Automations may archive only tasks they created and still identify reliably.
- Do not install an audio driver or create billable/provider resources without the user's approval of the exact action.

## Retained product behavior

These saved behaviors remain required even when they are implemented across successive milestones:

- Hermes is the on/off controller. The phone page cannot start Codex by itself.
- The user can request a new conversation or resume an existing one. Hermes infers clear intent, asks only when ambiguous, and can present up to ten recent visible conversations.
- Normal use requires no interaction with the PC: Hermes launches Codex, selects the conversation, starts Voice, verifies readiness, and only then supplies the client connection.
- Model and reasoning effort are explicit per-call choices. Hermes asks every time, discovers rather than hardcodes available options, and refuses to report ready until both still match after Voice startup.
- The browser page remains minimal: connection state, microphone mute, Codex-output mute, and End Session.
- A short break or connection drop uses a reconnect grace period without another pairing code. Device trust has an independently configurable expiry.
- Ending the call stops the remote media and Voice session but preserves the underlying Codex task and any work it is doing.
- The page address may be permanent or provider-assigned; the user does not manage it because Hermes sends the current usable link.
- Remote infrastructure is user-owned. No mandatory shared project service or custom domain is required.
- Supported clients are capability-based phone browsers, not one particular iPhone. iOS Safari/WebKit and Android Chromium are qualification targets.
- Same-host Hermes ships first, but separate-host Hermes remains a planned supported topology.
- The optional Discord voice adapter remains part of the roadmap and reuses the same Codex, Voice, audio, and lifecycle core.

## Execution rules

- Build the smallest runnable slice before production architecture.
- One worker implementation pass and one short Codex review per milestone.
- Block only broken core behavior, credential/privacy exposure, data loss, or unsafe system/external mutation.
- Log minor robustness issues as hardening debt.
- Five successful consecutive calls are enough for MVP acceptance; exhaustive compatibility and adversarial suites belong to release hardening.

## Milestones

| ID | Milestone | Pass condition |
|---|---|---|
| MVP-01 | Windows audio path | Programmatic audio reaches `CABLE Output` through VB-CABLE, and system output is captured in memory without saving recordings. |
| MVP-02 | Hermes-controlled local Codex Voice | From Telegram, Hermes supports the saved new/resume conversation flow: infer when clear, ask when ambiguous, show up to ten visible recent conversations when needed, open the confirmed conversation, ask for model and effort, and use deterministic tools for Voice/audio lifecycle. It launches Codex, continuously routes the configured physical microphone through VB-CABLE, verifies model and effort again after real Voice starts, and stops Voice/audio without deleting or cancelling the task. No manual Codex interaction is required at runtime. |
| MVP-03 | Local browser call | A broadly compatible phone browser on the LAN holds one intelligible two-way audio conversation with the Hermes-started Codex Voice session for five minutes. The minimal page includes connection state, microphone mute, Codex-output mute, and End Session; reconnect during the grace period does not require a new code; ending preserves the Codex task. |
| MVP-04 | User-owned remote route | The same flow works away from home through a user-owned Cloudflare route with no custom domain required. Hermes is the on switch and sends the current usable link only after Voice and the route are ready. The permanent page cannot start Codex by itself; device trust and live-session authorization remain separate. |
| MVP-05 | Usable package | One guided setup checks Codex/sign-in/Voice, Hermes topology, VB-CABLE, provider connection, and phone pairing. It installs the plugin and companion as one product, provides status/repair/uninstall, enforces one active session, and passes five consecutive calls on the reference setup. |
| MVP-06 | Compatibility and topology hardening | Representative iOS Safari/WebKit and Android Chromium testing, foreground/background expectations, clearer failures, separate-host Hermes support, and installation documentation. |
| MVP-07 | Optional Discord adapter | A user-owned Discord bot reuses the same lifecycle/audio core in one authorized voice channel. Post-MVP only. |

## Current work

MVP-01 is complete on the reference PC. The local Python spike proves playback and in-memory WASAPI system-output loopback; 18 focused tests pass. The user installed the official VB-CABLE driver, an in-memory test proved the cable route, and a continuous WASAPI callback from the Blue Snowball into `CABLE Input` was heard successfully by real Codex Voice. No audio was saved.

MVP-02 is complete on the reference PC. Version 0.3.0 is committed, pushed, installed, enabled, and loaded by the active gateway. A real Telegram request successfully used the saved task flow, asked for model and effort, started actual Codex Voice, and carried continuously routed Blue Snowball audio into it. The installed companion separately passed start/status/stop lifecycle checks; the owner declined a redundant Telegram stop click, which is recorded as unexercised orchestration rather than an MVP blocker. Unit/integration fakes total 35. Strong stable-ID task automation remains hardening work.

MVP-03 is active. Its one-peer local WebRTC page forwards browser microphone audio to VB-CABLE and exposes mute/end/test controls, microphone selection, local activity feedback, and bounded peer/browser-audio/CABLE status. The owned host now remains available while Hermes is still confirming Codex Voice and stops only on an explicit stop request. The return path uses Windows process-loopback capture scoped to the unique current-session Codex process tree. On the reference PC, 89 Python tests pass in the Hermes runtime, the native capture route activates and cleans up, and installed plugin version 0.5.0 passed a start/status/pause/status/stop lifecycle check. No endpoint-wide fallback or audio persistence exists. One successful live browser-to-Codex-to-browser conversation remains before local acceptance; trusted phone HTTPS, pairing, and reconnect follow without exposing the unauthenticated localhost spike.
