---
name: hermes_voice
description: >-
  Start, resume, check, or stop the real Codex desktop Voice session on this
  Windows PC. Use for Telegram or local requests such as start Codex Voice,
  start a new Codex Voice conversation, resume Codex Voice, continue a Codex
  conversation by Voice, stop Codex Voice, or switch Codex to CABLE Output.
  Orchestrate codex_voice_start, app-scoped computer_use, then
  codex_voice_confirm. Do not wait for a slash command.
version: 0.2.0
platforms:
  - windows
metadata:
  hermes:
    tags: [codex, voice, windows, computer_use]
---

# hermes_voice

When the user asks to start, resume, check, or stop Codex Voice on this PC, follow this skill. Do not wait for a slash command. Call the registered Voice tools plus the real Hermes tool `computer_use`. Do not operate Codex with shell commands, UI click scripts, OCR, raw coordinates, or unscoped desktop automation.

Companion tools own preflight, packaged Codex launch, VB-CABLE endpoint presence, session state, and task-preserving cleanup. `computer_use` owns every visible Codex control: new or recent conversation, Voice start, microphone selection, visible ready check, and Voice stop.

## Tools

- `codex_voice_start`: requires `mode`. Preflights the unlocked Windows session, launches Codex if needed, proves `CABLE Output (VB-Audio Virtual Cable)` exists as a capture endpoint, and returns `starting`. It does not click New task, Voice, or the microphone. Never pass task IDs, titles, or App Server resume keys.
- `codex_voice_confirm`: records `ready` only after app-scoped `computer_use` showed Voice visibly active and exact `CABLE Output (VB-Audio Virtual Cable)` selected. Requires `voice_visible=true` and `cable_selected=true`. Call only while status is `starting`. Missing or false flags keep status `starting` and must not claim completion.
- `codex_voice_status`: returns `inactive`, `starting`, `ready`, `stopping`, or `failed`.
- `codex_voice_stop`: clears companion state after `computer_use` ended Voice and a post-action capture showed Voice ended. Leaves the Codex task open. Never delete, cancel, archive, or close the task.

A UIA ready-name miss is not proof Voice failed and is not permission to skip microphone selection. Never call `codex_voice_confirm` because a generic name such as Stop voice was or was not found by UIA.

## Infer, ask, list, select

Infer `new` versus `current` when the request is clear. A request such as "start a new Codex Voice conversation" is `mode="new"`. A request to continue, resume, or use a named or currently open conversation is `mode="current"` after that conversation is selected in Codex.

If new versus resume is ambiguous, ask. Do not call `codex_voice_start` until the user confirms.

When the requested conversation is unclear, use `computer_use` with an app-scoped accessibility capture (`action="capture"`, `mode="ax"`, `app` set to Codex or ChatGPT) to collect up to ten visible recent conversation names. Send a numbered list. Use an app-scoped SOM capture (`mode="som"`) only if accessibility capture is insufficient. After the user confirms, click the matching element with `computer_use` (`action="click"`, `element=N`). Claim selection only after a post-action app-scoped capture (`capture_after=True` or a follow-up capture) shows the requested visible title selected or open.

Duplicate or ambiguous names require the user to choose. Do not guess when names are duplicate or ambiguous. Never use raw coordinates. Never inspect conversation contents. Never persist a screenshot, accessibility tree, or name list.

## New sequence

1. `codex_voice_start` with `mode="new"` until status is `starting`.
2. App-scoped `computer_use` clicks New task or New chat and verifies a new conversation is open.
3. App-scoped `computer_use` starts Voice and verifies Voice is visibly active.
4. App-scoped `computer_use` opens the Voice microphone or settings control, selects exactly `CABLE Output (VB-Audio Virtual Cable)`, and verifies that value is selected. Accessibility capture first. SOM only if needed. Element targeting only.
5. `codex_voice_confirm` with `voice_visible=true` and `cable_selected=true`.
6. Tell the user Voice is ready only after confirm returns `ready`.

## Resume sequence

1. `codex_voice_start` with `mode="current"` until status is `starting` if Codex must be launched first. If Codex is already open and the conversation is unclear, list then select first.
2. Verify the requested visible title is selected or open with app-scoped `computer_use` before Voice.
3. App-scoped `computer_use` starts Voice, verifies Voice is visible, selects and verifies exact CABLE Output.
4. `codex_voice_confirm` with `voice_visible=true` and `cable_selected=true`.

## Stop sequence

1. App-scoped `computer_use` ends Voice and a post-action capture shows Voice ended.
2. `codex_voice_stop` to clear companion state.
3. Leave the Codex task open.

## Rules

Same-host Windows only. The user session must be awake and unlocked. One owned Voice session. If confirm already returned `ready` from this plugin, `codex_voice_start` is idempotent. Do not take over an unowned Voice session. If Voice is already visibly active and unowned, ask or stop it with `computer_use` only after the user confirms.

App Server or CP-013 stable-ID resume stays out of scope. Never pass `task_id`, `thread_id`, `title`, or `resume`. Never touch the preserved CP-013 disposable task.

Voice microphone must be `CABLE Output (VB-Audio Virtual Cable)`. Endpoint installation is not selection proof. If that endpoint is missing, `codex_voice_start` fails with `cable_mic_missing` and you must stop. If computer_use cannot select it, do not confirm. Do not fall back to the physical PC microphone.

Do not log prompts, task titles, transcripts, or audio. Read only `ok`, `status`, and `error` from tool results.
