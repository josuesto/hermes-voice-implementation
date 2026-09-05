---
name: hermes_voice
description: >-
  Start, resume, check, or stop the real Codex desktop Voice session on this
  Windows PC. Use for Telegram or local requests such as start Codex Voice,
  summon Codex, dismiss Codex, start a new Codex Voice conversation, resume
  Codex Voice, continue a Codex conversation by Voice, start a Discord voice
  call, send a browser call link, start a phone or remote call, stop Codex
  Voice, or switch Codex to CABLE Output.
  Always ask which Codex model and reasoning effort to use for the call, then
  orchestrate codex_voice_start, app-scoped computer_use, and
  codex_voice_confirm. Do not wait for a slash command.
version: 0.6.0
platforms:
  - windows
metadata:
  hermes:
    tags: [codex, voice, windows, computer_use, browser, discord]
---

# hermes_voice

When the user asks to start, resume, check, or stop Codex Voice on this PC, follow this skill. Natural aliases are "summon Codex" for start and "dismiss Codex" for explicit stop. Do not wait for a slash command. Call the registered Voice tools plus the real Hermes tool `computer_use`. Do not operate Codex with shell commands, UI click scripts, OCR, raw coordinates, or unscoped desktop automation.

Companion tools own preflight, packaged Codex launch, one audio transport, session state, and task-preserving cleanup. `computer_use` owns the visible Codex controls needed at runtime: new or recent conversation, model, reasoning effort, Voice start, visible ready check, and Voice stop. `CABLE Output (VB-Audio Virtual Cable)` is selected once in Codex Settings during setup; it is not selected inside each Voice call.

## Tools

- `codex_voice_start`: requires `mode` and `transport`. Preflights the unlocked Windows session, launches Codex if needed, and proves VB-CABLE exists. `transport="physical_mic"` starts the configured physical microphone stream into `CABLE Input (VB-Audio Virtual Cable)`. `transport="browser"` starts the loopback-only WebRTC server and does not start the physical microphone router. `transport="discord"` starts the owned Discord sidecar into one configured private guild voice channel and does not start the physical microphone router or the browser server. Returns `starting`. It does not click New task or Voice. Never pass task IDs, titles, URLs, or App Server resume keys.
- `codex_voice_confirm`: records `ready` only after app-scoped `computer_use` showed Voice visibly active and re-verified the user-selected model and effort after Voice startup. Requires `voice_visible=true`, `model_verified=true`, and `effort_verified=true`. Call only while status is `starting`. A missing or false flag keeps status `starting` and must not claim completion. For browser transport, the allowlisted localhost `url` is returned only after confirm returns `ready`. For Discord transport, both audio directions stay gated until confirm succeeds and the voice channel is actually connected.
- `codex_voice_status`: returns `inactive`, `starting`, `ready`, `stopping`, or `failed`. For an active owned browser transport it may include the allowlisted localhost `url` plus bounded `peer`, `browser_audio`, and `cable` enums. For an active owned Discord transport it may include bounded `connection`, `audience`, `incoming`, `cable`, and `outgoing` enums. Physical-mic results never include those fields. Never read a channel URL, token, name, or ID from tool results.
- `codex_voice_stop`: stops the owned physical-mic router, browser-call server, or Discord sidecar and clears companion state. Call this only after the user explicitly asks to stop, end, or dismiss Codex Voice, and only after `computer_use` ended Voice and a post-action capture showed Voice ended. Leaves the Codex task open. Never delete, cancel, archive, or close the task.

A UIA ready-name miss is not proof Voice failed and is not permission to skip microphone selection. Never call `codex_voice_confirm` because a generic name such as Stop voice was or was not found by UIA.

## Transport

Infer `transport="discord"` when the user asks to summon Codex, start a Discord voice call, or join Discord voice.

Infer `transport="browser"` when the user asks for a link, a browser call, a phone call, or a remote call.

Infer `transport="physical_mic"` only when the request clearly says to use the PC microphone.

If transport is ambiguous, ask which one to use. Do not call `codex_voice_start` until the user confirms. Never start more than one transport. Switching transport while a session is `starting` or `ready` fails until `codex_voice_stop`. Discord never starts the physical microphone router or the browser server.

Browser Leave call on the page closes only the WebRTC peer. It does not stop Codex Voice and does not stop the owned server. The user can open the same localhost link again while Hermes's session remains `starting` or `ready`.

A brief Discord leave and rejoin must not stop Codex Voice, must not replay queued speech, and must not end the Codex task. While the owner is absent, or while an extra participant is in the channel, both audio directions stay paused and status reports `waiting_for_owner` or `audience_blocked`.

The owned browser server or Discord sidecar must stay available across Hermes turn completion, uncertainty, `computer_use` failure, and inability to verify model or effort. Never call `codex_voice_stop` as failure cleanup. Never stop because confirmation is incomplete, because `computer_use` failed, or because the Hermes turn is ending. Report the incomplete state, call `codex_voice_status`, and leave the owned transport running. If status includes `url` while still `starting`, you may send that allowlisted link so the user can open the page.

Send the browser link from a `ready` confirm result when confirmation succeeds. The only allowed URL is `http://127.0.0.1:8765/`. Never invent, accept, or forward a different URL. Discord results never include a URL.

## Model and effort are mandatory per call

For every Voice start, ask the user which currently available Codex model and reasoning effort they want. Do this for new and resumed conversations. Never silently reuse the existing values. If the original request already names both, ask the user to confirm those exact choices before changing the UI.

After the target conversation is open, use an app-scoped accessibility capture to read the current model and effort selectors and their visible choices. Present the currently available choices; do not rely on a hardcoded model or effort list. Use app-scoped `computer_use` to choose exactly what the user confirmed, then capture again and verify both selectors.

Start Voice only after that first verification. Voice can change model or effort automatically, so re-check both selectors after Voice becomes visible. If either changed, reselect the user's choice and verify again. Do not claim ready and do not call `codex_voice_confirm` until the post-Voice capture supports `model_verified=true` and `effort_verified=true`. If the selectors are unavailable or the requested combination is unavailable, explain that, keep the owned transport running, and ask for another visible choice. Never persist selector values or option lists. Never call `codex_voice_stop` because verification failed.

## Infer, ask, list, select

Infer `new` versus `current` when the request is clear. A request such as "start a new Codex Voice conversation" is `mode="new"`. A request to continue, resume, or use a named or currently open conversation is `mode="current"` after that conversation is selected in Codex.

If new versus resume is ambiguous, ask. Do not call `codex_voice_start` until the user confirms.

When the requested conversation is unclear, use `computer_use` with an app-scoped accessibility capture (`action="capture"`, `mode="ax"`, `app` set to Codex or ChatGPT) to collect up to ten visible recent conversation names. Send a numbered list. Use an app-scoped SOM capture (`mode="som"`) only if accessibility capture is insufficient. After the user confirms, click the matching element with `computer_use` (`action="click"`, `element=N`). Claim selection only after a post-action app-scoped capture (`capture_after=True` or a follow-up capture) shows the requested visible title selected or open.

Duplicate or ambiguous names require the user to choose. Do not guess when names are duplicate or ambiguous. Never use raw coordinates. Never inspect conversation contents. Never persist a screenshot, accessibility tree, or name list.

## New sequence

1. `codex_voice_start` with `mode="new"` and the inferred `transport` until status is `starting`.
2. App-scoped `computer_use` clicks New task or New chat and verifies a new conversation is open.
3. Inspect the visible model and effort choices, ask the user, set both, and verify both.
4. App-scoped `computer_use` starts Voice and verifies Voice is visibly active.
5. Re-check model and effort after Voice starts; correct and verify any automatic change.
6. `codex_voice_confirm` with `voice_visible=true`, `model_verified=true`, and `effort_verified=true`.
7. Tell the user Voice is ready only after confirm returns `ready`. For browser transport, send `url` only after that ready result.

## Resume sequence

1. `codex_voice_start` with `mode="current"` and the inferred `transport` until status is `starting` if Codex must be launched first. If Codex is already open and the conversation is unclear, list then select first.
2. Verify the requested visible title is selected or open with app-scoped `computer_use` before Voice.
3. Inspect the visible model and effort choices, ask the user, set both, and verify both.
4. App-scoped `computer_use` starts Voice and verifies Voice is visible.
5. Re-check model and effort after Voice starts; correct and verify any automatic change.
6. `codex_voice_confirm` with `voice_visible=true`, `model_verified=true`, and `effort_verified=true`.
7. For browser transport, send `url` only after confirm returns `ready`.

## Stop sequence

Call this sequence only when the user explicitly asks to stop, end, or dismiss Codex Voice. Incomplete confirmation, a `computer_use` failure, setup trouble, and Hermes turn completion are not stop requests.

1. App-scoped `computer_use` ends Voice and a post-action capture shows Voice ended.
2. `codex_voice_stop` to stop the owned transport and clear companion state.
3. Leave the Codex task open.

## Rules

Same-host Windows only. The user session must be awake and unlocked. One owned Voice session. If confirm already returned `ready` from this plugin, `codex_voice_start` with the same transport is idempotent. Do not take over an unowned Voice session. If Voice is already visibly active and unowned, ask or stop it with `computer_use` only after the user confirms.

App Server or CP-013 stable-ID resume stays out of scope. Never pass `task_id`, `thread_id`, `title`, or `resume`. Never touch the preserved CP-013 disposable task.

Voice microphone must already be `CABLE Output (VB-Audio Virtual Cable)` in Codex Settings. The user performs and verifies this one-time setup; Codex does not expose the device selector inside an active Voice call. The physical source is configured in `%HERMES_HOME%\config\hermes_voice.json` under `source_microphone`, or with `HERMES_VOICE_SOURCE_MIC`. If either endpoint or the configured source is unavailable, start fails closed. Do not attempt per-call device selection and never silently fall back to another physical microphone.

Do not log prompts, task titles, transcripts, or audio. Read only `ok`, `status`, `error`, `url`, `peer`, `browser_audio`, `cable`, `connection`, `audience`, `incoming`, and `outgoing` from tool results. Physical-mic results never include `url`, `peer`, `browser_audio`, `cable`, `connection`, `audience`, `incoming`, or `outgoing`. Browser `peer` is `none`, `connecting`, `connected`, or `failed`. Browser audio is `no-peer`, `silent`, or `receiving`. Discord `connection` is `idle`, `connecting`, `connected`, or `failed`. Discord `audience` is `waiting_for_owner`, `owner_present`, or `audience_blocked`. Discord incoming audio is `silent`, `receiving`, or `failed`. Discord outgoing audio is `silent`, `sending`, or `failed`. CABLE forwarding is `inactive`, `forwarding`, or `failed`.
