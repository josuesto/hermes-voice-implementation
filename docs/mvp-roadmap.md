# Hermes Voice Implementation — MVP Roadmap

Status: active execution roadmap
Decision date: 2026-09-01

This roadmap supersedes the legacy checkpoint map as the gate for the first working prototype. The detailed checkpoint material remains useful research and later hardening guidance, but it no longer blocks vertical-slice implementation.

## MVP contract

- Windows only; the PC is on, awake, unlocked, signed into Windows, and already signed into Codex.
- Same-host Hermes first.
- One user and one active remote Voice session.
- New Codex task only. Existing-task resume is deferred.
- Manual setup is acceptable, but normal session startup is not. Hermes must launch Codex, create a fresh task, and start Voice before any end-to-end call is considered working.
- LAN first, then user-owned Cloudflare remote access.
- Browser call first; Discord remains post-MVP.

## Safety floor

- Never request, log, or publish credentials, prompts, task contents, transcripts, or audio.
- Never delete a Codex task.
- Automations may archive only tasks they created and still identify reliably.
- Do not install an audio driver or create billable/provider resources without the user's approval of the exact action.

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
| MVP-02 | Hermes-controlled local Codex Voice | A same-host Hermes command launches Codex when needed, creates a fresh task, starts real Voice, positively verifies Voice ready, and can stop Voice without deleting or cancelling the task. No manual Codex interaction is required at runtime. |
| MVP-03 | Local browser call | A phone browser on the LAN holds one intelligible two-way audio conversation with the Hermes-started Codex Voice session for five minutes; Hermes returns the usable link and can stop the bridge without deleting the task. |
| MVP-04 | User-owned remote route | The same flow works away from home through a user-owned Cloudflare route with no custom domain required. |
| MVP-05 | Usable package | One setup path, reconnect/end controls, cleanup, and five consecutive successful calls on the reference setup. |
| MVP-06 | Compatibility hardening | Representative iOS Safari/WebKit and Android Chromium testing, clearer failures, and installation documentation. |
| MVP-07 | Optional Discord adapter | A user-owned Discord bot reuses the same lifecycle/audio core in one authorized voice channel. Post-MVP only. |

## Current work

MVP-01 is complete on the reference PC. The local Python spike proves playback and in-memory WASAPI system-output loopback; 13 focused tests pass. The user installed the official VB-CABLE driver, and an in-memory test proved the `CABLE Input -> CABLE Output` route (`peak=0.200001`, 62,400 frames discarded, no audio saved). MVP-02 is active: same-host Hermes must now launch a fresh Codex task, start Voice, verify ready, and own stop/cleanup. The next end-to-end audio injection test happens only after that orchestration succeeds. CP-013 existing-task resume remains deferred, and its preserved disposable task must not be touched.
