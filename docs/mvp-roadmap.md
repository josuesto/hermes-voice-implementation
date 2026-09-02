# Hermes Voice Implementation — MVP Roadmap

Status: active execution roadmap
Decision date: 2026-09-01

This roadmap supersedes the legacy checkpoint map as the gate for the first working prototype. The detailed checkpoint material remains useful research and later hardening guidance, but it no longer blocks vertical-slice implementation.

## MVP contract

- Windows only; the PC is on, awake, unlocked, signed into Windows, and already signed into Codex.
- Same-host Hermes first.
- One user and one active remote Voice session.
- New Codex task only. Existing-task resume is deferred.
- Manual setup or one manual UI step is acceptable while proving the first slice.
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
| MVP-01 | Local Codex Voice and Windows audio spike | Codex Voice starts locally; audio can be fed into its selected input and its output can be captured/returned without saving recordings. Manual Voice interaction is allowed. |
| MVP-02 | Local browser call | A phone browser on the LAN holds one intelligible two-way audio conversation with Codex Voice for five minutes. |
| MVP-03 | Hermes control | A Telegram request starts the local bridge and a fresh Codex Voice task, returns the usable link, and can stop the bridge without deleting the task. |
| MVP-04 | User-owned remote route | The same flow works away from home through a user-owned Cloudflare route with no custom domain required. |
| MVP-05 | Usable package | One setup path, reconnect/end controls, cleanup, and five consecutive successful calls on the reference setup. |
| MVP-06 | Compatibility hardening | Representative iOS Safari/WebKit and Android Chromium testing, clearer failures, and installation documentation. |
| MVP-07 | Optional Discord adapter | A user-owned Discord bot reuses the same lifecycle/audio core in one authorized voice channel. Post-MVP only. |

## Current work

MVP-01 is active. The local Python spike proves playback and in-memory WASAPI system-output loopback; 13 focused tests pass. No programmable virtual microphone is installed, so audio injection into Codex Voice awaits the user's decision on the official VB-CABLE driver. CP-013 exact existing-task resume and its evidence harness are deferred to hardening. The preserved disposable CP-013 test task is not part of MVP-01 and must not be touched by automation.
