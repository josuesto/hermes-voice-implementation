---
name: hermes_voice
description: Start, status, and stop the real Codex desktop Voice session on this Windows PC through dedicated tools. Use when the user asks Hermes to start Codex Voice, resume a Codex Voice conversation, check Voice, or stop Voice.
version: 0.1.1
platforms:
  - windows
metadata:
  hermes:
    tags: [codex, voice, windows]
---

# hermes_voice

Call the registered Voice tools for start, status, and stop. Do not operate Codex with shell commands, UI click scripts, OCR, raw coordinates, or unscoped desktop automation. Conversation picking uses the real Hermes tool `computer_use` only, scoped to the Codex desktop app.

## Tools

- `codex_voice_start`: requires `mode`. `mode="new"` launches Codex if needed, creates a fresh task, starts Voice, selects and verifies `CABLE Output (VB-Audio Virtual Cable)`, then reports ready. `mode="current"` launches Codex if needed, does not create or close a task, starts Voice on the conversation already selected in Codex, then selects and verifies CABLE Output. Never pass task IDs, titles, or App Server resume keys.
- `codex_voice_status`: returns `inactive`, `starting`, `ready`, `stopping`, or `failed`.
- `codex_voice_stop`: stops Voice only. Leaves the Codex task open. Never delete, cancel, archive, or close the task.

## Infer, ask, list, select

Infer `new` versus `current` when the request is clear. A request such as "start a new Codex Voice conversation" is `mode="new"`. A request to continue, resume, or use a named or currently open conversation is `mode="current"` after that conversation is selected in Codex.

If new versus resume is ambiguous, ask. Do not call `codex_voice_start` until the user confirms.

When the requested conversation is unclear, use `computer_use` with an app-scoped accessibility capture (`action="capture"`, `mode="ax"`, `app` set to Codex or ChatGPT) to collect up to ten visible recent conversation names. Send a numbered list. Use an app-scoped SOM capture (`mode="som"`) only if accessibility capture is insufficient. After the user confirms, click the matching element with `computer_use` (`action="click"`, `element=N`). Claim selection only after a post-action app-scoped capture (`capture_after=True` or a follow-up capture) shows the requested visible title selected or open. Then call `codex_voice_start` with `mode="current"`.

Duplicate or ambiguous names require the user to choose. Do not guess when names are duplicate or ambiguous. Never use raw coordinates. Never inspect conversation contents. Never persist a screenshot, accessibility tree, or name list.

Do not use `computer_use` to click New task, New chat, Voice, or the microphone. The companion owns those actions after `codex_voice_start`.

## Rules

Same-host Windows only. The user session must be awake and unlocked. One owned Voice session. If Voice is already ready from this plugin, `codex_voice_start` is idempotent. If Voice is active and unowned, fail instead of taking it over.

App Server or CP-013 stable-ID resume stays out of scope. Never pass `task_id`, `thread_id`, `title`, or `resume`. Never touch the preserved CP-013 disposable task.

Voice microphone must be `CABLE Output (VB-Audio Virtual Cable)`. If that endpoint is missing or cannot be selected as a named accessible control, return the tool error and stop. Do not fall back to the physical PC microphone.

Do not log prompts, task titles, transcripts, or audio. Read only `ok`, `status`, and `error` from tool results.
