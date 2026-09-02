---
name: hermes_voice
description: Start, status, and stop the real Codex desktop Voice session on this Windows PC through dedicated tools. Use when the user asks Hermes to start Codex Voice, check Voice, or stop Voice.
version: 0.1.0
platforms:
  - windows
metadata:
  hermes:
    tags: [codex, voice, windows]
---

# hermes_voice

Call the registered tools. Do not operate Codex with shell commands, UI click scripts, screenshots, OCR, or computer-use.

## Tools

- `codex_voice_start`: launch Codex if needed, create a fresh task, start Voice, select and verify `CABLE Output (VB-Audio Virtual Cable)`, then report ready. No task ID or title arguments.
- `codex_voice_status`: returns `inactive`, `starting`, `ready`, `stopping`, or `failed`.
- `codex_voice_stop`: stops Voice only. Leaves the Codex task open. Never delete, cancel, archive, or close the task.

## Rules

Same-host Windows only. The user session must be awake and unlocked. One owned Voice session. If Voice is already ready from this plugin, `codex_voice_start` is idempotent. If Voice is active and unowned, fail instead of taking it over.

Existing-task resume is unsupported. Never search for, open, or name an existing task. Never touch the preserved CP-013 disposable task.

Voice microphone must be `CABLE Output (VB-Audio Virtual Cable)`. If that endpoint is missing or cannot be selected as a named accessible control, return the tool error and stop. Do not fall back to the physical PC microphone.

Do not log prompts, task titles, transcripts, or audio. Read only `ok`, `status`, and `error` from tool results.
