# MVP-D01 implementation review

Date: 2026-09-04.
Status: implementation accepted for private setup; installation and live-call acceptance pending.

The Discord transport is implemented in the companion and Hermes plugin version 0.6.0. It preserves the real Codex Voice engine, owner-controlled new/current conversation selection, per-call model/effort checks, one transport at a time, and no recording or transcription.

The focused review verified the configured-channel/Ready authorization gate, bounded stream buffering, exact-owned-child stop under a blocked pipe writer, partial-start cleanup, and reconnect recovery. The final reconnect test uses the production session runtime and verifies replacement-connection playback subscription, owner receive, stale queue removal, and audience gating.

## Evidence

- Final independent Node suite: 15 passed, 0 failed.
- DAVE/Opus dependency load check: exit 0, without Discord login.
- Focused Discord Python in the preceding review: 15 passed, including stuck-writer stop and failed-source cleanup. Python was unchanged by the final Node correction and was not rerun.
- Whitespace/diff checks passed.
- The worker reported 109 combined Python tests passing. The independent combined run instead timed out at the existing browser WebRTC leave/reconnect test. This parked browser limitation remains unverified; it is not silently counted as a pass and does not reopen browser work as a Discord prerequisite.

These are offline checks using fake devices/connections and synthetic data. They do not prove live Discord receive, audio latency, phone compatibility, or Codex audibility.

## Next acceptance boundary

Follow the [private setup requirements](../companion/discord_voice/SETUP.md) and [MVP-D01 plan](mvp-d01-discord-voice.md). The owner supplies a bot and private voice channel and enters credentials locally. The reviewed package must be installed into the Hermes runtime and the gateway restarted before testing. Nothing in this publication claims those actions have occurred.

One real five-minute call must prove Hermes startup and model/effort confirmation, intelligible speech both ways, mute, a brief leave/rejoin without replay, persistence across a Hermes turn, and explicit stop that preserves the Codex task. Only then is MVP-D01 complete. Five consecutive successful calls remain the later packaging target.
