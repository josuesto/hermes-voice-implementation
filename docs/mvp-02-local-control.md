# MVP-02 local Hermes Codex Voice control

Development slice for same-host Windows. Hermes calls three tools. The user does not open Codex, create the task, or click Voice. Phone and browser work are out of scope. Existing-task resume is out of scope. Do not touch the preserved CP-013 disposable task.

## Layout

- `plugin/hermes_voice/` is the Hermes plugin (`register(ctx)` with `ctx.register_tool`).
- `companion/codex_control.py` is the Windows companion: packaged Codex activation, fresh-task UIA scoped to the unique Codex window, Voice start, then VB-CABLE microphone select/verify, then ready/stop.
- Status values: `inactive`, `starting`, `ready`, `stopping`, `failed`.
- Tool JSON keys: `ok`, `status`, and `error` when failed.

## Development install

From the repo root, after Codex review (do not enable until then):

```
$repo = (Resolve-Path ".").Path
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
$dest = Join-Path $hermesHome "plugins\hermes_voice"
New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Copy-Item -Recurse (Join-Path $repo "plugin\hermes_voice") $dest
Copy-Item -Recurse (Join-Path $repo "companion") (Join-Path $dest "companion")
hermes plugins enable hermes_voice
```

Restart the Hermes gateway after enable so Telegram can see the tools. Load skill `hermes_voice:codex_voice` when you want the written tool rules in context.

Python extras used by the companion: `soundcard`, `numpy`, and `comtypes`. The existing `prototype/windows-bridge/.venv` already has `soundcard` and `numpy`. Install `comtypes` into the environment that runs Hermes if Voice UIA invoke is required:

```
python -m pip install comtypes
```

## Tests

Audio spike (13) plus companion/plugin fakes (19):

```
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s prototype\windows-bridge\tests -v
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s companion -v
```

## One-cycle acceptance (do not run until Codex review)

1. PC awake, unlocked, signed into Codex. VB-CABLE installed. Start opens Voice first, then selects `CABLE Output (VB-Audio Virtual Cable)` and verifies it before reporting ready.
2. Telegram to same-host Hermes: start Codex Voice.
3. Hermes calls `codex_voice_start` only. Status becomes `ready`. Voice ready is a Stop voice or Mute microphone control, not merely a Codex process. The microphone is the named CABLE Output control, not a physical mic.
4. Play a short non-sensitive phrase into `CABLE Input`. Codex hears it on `CABLE Output`.
5. Telegram: stop Voice. Hermes calls `codex_voice_stop`. Status becomes `inactive`. The fresh task remains open. No delete, cancel, archive, or Codex kill.

## Limits

- One owned Voice session.
- `codex_voice_start` is idempotent when that session is already ready.
- Unowned Voice fails with `conflicting_voice`.
- Missing or unselected CABLE Output fails closed. The physical PC microphone is never a silent fallback.
- No force-kill of Codex. Stop releases companion state and Voice only.
