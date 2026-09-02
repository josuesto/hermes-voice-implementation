# Project pause handoff — 2026-09-02

Status: intentionally paused so the owner can prioritize other projects.

This document is the shortest safe path back into the work. The full product direction remains in [the plan](plan.md), while [the MVP roadmap](mvp-roadmap.md) is the active execution sequence. The older CP-013 task-correlation program remains deferred hardening work and should not block the browser MVP.

## Accepted state

- `main` is public and synchronized through the pause commit that adds this handoff. The immediately preceding implementation commit is `cbf1d74` (`fix: keep browser voice sessions observable`).
- MVP-01 is accepted: VB-CABLE is installed on the reference Windows PC, and the continuous Blue Snowball → `CABLE Input` → `CABLE Output` → real Codex Voice path worked.
- MVP-02 is accepted: Hermes can launch/control the real Codex desktop Voice flow, distinguish new versus current tasks through app-scoped computer use, and ask for and verify model plus reasoning effort on every start.
- Installed Hermes plugin version `0.5.0` was enabled and loaded on the reference PC when the project was paused.
- MVP-03 implementation includes a loopback-only WebRTC page, browser microphone selection, an in-memory microphone activity meter, bounded `peer`/`browser_audio`/`cable` diagnostics, VB-CABLE forwarding, and Codex-process-only return capture.
- The owned browser host persists while confirmation is incomplete and is not stopped as failure cleanup. Installed code passed `start → status → pause → status → explicit stop`; the URL and diagnostics remained available until the explicit stop.
- Verification at pause: 18 Windows-audio tests, 48 companion/plugin/skill tests, and 23 browser/host tests passed in the actual Hermes Python runtime. `git diff --check` passed. No audio, prompts, transcripts, task contents, credentials, or raw browser/device identifiers were saved.

## Exact unfinished boundary

MVP-03 is not accepted yet. One successful live browser → VB-CABLE → Codex Voice → process-loopback → browser conversation has not been demonstrated after version `0.5.0` was installed.

The last failed live attempt occurred before the `0.5.0` lifecycle correction: Hermes left the session unconfirmed and then invoked stop as cleanup, so port 8765 was already closed when it was inspected. That attempt does not prove a remaining microphone or VB-CABLE defect. It also does not prove the corrected path works end to end. Treat the result as inconclusive.

The current page is localhost-only (`http://127.0.0.1:8765/`). It is suitable for the next same-PC validation but is not yet a phone-accessible remote link. HTTPS, pairing/device trust, a user-owned Cloudflare route, STUN/TURN behavior, representative phone testing, packaging, and the optional Discord adapter remain unimplemented.

## First resume procedure

1. Pull `main` and read this handoff plus the current MVP roadmap.
2. Verify Hermes reports `hermes_voice` enabled at version `0.5.0` or newer and that its gateway is running. Do not reinstall VB-CABLE unless endpoint discovery actually fails.
3. Through Telegram, ask Hermes to start a new Codex Voice conversation using the browser call. Choose the desired currently visible model and effort when asked.
4. Open the returned localhost page on the same PC, press **Start call**, grant microphone access, select Blue Snowball if it is not already selected, and confirm that the local activity meter moves while speaking.
5. Ask Hermes for Voice status. Interpret only the bounded fields:
   - `peer=connected`, `browser_audio=receiving`, `cable=forwarding`: the browser and VB-CABLE input path are alive; if Codex still hears nothing, verify Codex Settings still selects `CABLE Output (VB-Audio Virtual Cable)`.
   - `browser_audio=silent`: investigate browser permission, mute state, and selected microphone.
   - `peer=none|failed`: investigate page/WebRTC negotiation or whether the host is still listening.
   - `cable=inactive|failed` while browser audio is receiving: investigate the WASAPI sink or VB-CABLE endpoint.
6. Speak with Codex and verify returned Codex audio in the page. Use **Leave call** to test peer-only disconnection, then reconnect using the same page. Explicitly ask Hermes to stop only after the test.
7. If the two-way call passes, accept MVP-03 local validation and continue to trusted phone HTTPS/pairing. If it fails, fix only the diagnostic category identified above.

## Resume workflow

Codex remains the planner and acceptance authority. Grok 4.6 in Cursor implements one bounded slice. Codex performs a short risk-based review, requests at most focused rework, installs/tests accepted work, updates the living Obsidian note, then commits and pushes. Do not restore the earlier exhaustive review loop.

The next planned stages after local validation are the user-owned Cloudflare route, packaging and compatibility work, and—after the browser release—the optional user-owned Discord voice adapter.
