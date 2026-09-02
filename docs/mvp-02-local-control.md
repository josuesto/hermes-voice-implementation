# MVP-02 local Hermes Codex Voice control

Development slice for same-host Windows. Phone and browser work are out of scope. App Server and CP-013 stable-ID resume stay out of scope. Do not touch the preserved CP-013 disposable task.

Hermes `computer_use` owns visible Codex UI. Companion tools own preflight, packaged launch, VB-CABLE endpoint presence, session state, and cleanup. A Telegram request such as start Codex Voice should load the indexed skill without a slash command.

## Layout

- `skills/hermes_voice/SKILL.md` is the indexed skill source of truth.
- `plugin/hermes_voice/` is the Hermes plugin (`register(ctx)` with `ctx.register_tool`). Its SKILL.md copy must match the indexed file.
- `companion/codex_control.py` is the Windows companion: session lock, packaged Codex activation, unique window proof, endpoint presence, `starting`/`ready`/`inactive` state.
- Status values: `inactive`, `starting`, `ready`, `stopping`, `failed`.
- Tool JSON keys: `ok`, `status`, and `error` when failed.

## Development install

From the repo root, after Codex review (do not enable until then):

```
$repo = (Resolve-Path ".").Path
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
$pluginDest = Join-Path $hermesHome "plugins\hermes_voice"
$skillDest = Join-Path $hermesHome "skills\hermes_voice"
New-Item -ItemType Directory -Force -Path (Split-Path $pluginDest) | Out-Null
New-Item -ItemType Directory -Force -Path $skillDest | Out-Null
if (Test-Path $pluginDest) { Remove-Item $pluginDest -Recurse -Force }
Copy-Item -Recurse (Join-Path $repo "plugin\hermes_voice") $pluginDest
Copy-Item -Recurse (Join-Path $repo "companion") (Join-Path $pluginDest "companion")
Copy-Item -Force (Join-Path $repo "skills\hermes_voice\SKILL.md") (Join-Path $skillDest "SKILL.md")
hermes plugins enable hermes_voice
```

Restart the Hermes gateway after enable so Telegram can see the tools. The indexed skill `hermes_voice` is what a normal request should load. The plugin-registered copy is fallback only.

Python extras used by the companion: `soundcard`, `numpy`, and `comtypes`. The existing `prototype/windows-bridge/.venv` already has `soundcard` and `numpy`.

## Tests

Audio spike (13) plus companion/plugin/skill fakes (30):

```
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s prototype\windows-bridge\tests -v
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s companion -v
```

## Tool sequence

New:

1. `codex_voice_start` `mode=new` returns `starting`.
2. App-scoped `computer_use` creates the fresh conversation.
3. App-scoped `computer_use` starts Voice and verifies it is visible.
4. App-scoped `computer_use` selects and verifies `CABLE Output (VB-Audio Virtual Cable)`.
5. `codex_voice_confirm` `voice_visible=true` `cable_selected=true` returns `ready`.

Resume:

1. `codex_voice_start` `mode=current` returns `starting` (launch first when Codex is closed).
2. App-scoped `computer_use` lists up to ten visible names if needed, user chooses duplicates, then verifies the title is selected or open.
3. App-scoped `computer_use` starts Voice, verifies Voice, selects and verifies CABLE Output.
4. `codex_voice_confirm` returns `ready`.

Stop:

1. App-scoped `computer_use` ends Voice and a post-action capture shows it ended.
2. `codex_voice_stop` returns `inactive`. The Codex task remains open.

## One-cycle acceptance (do not run until Codex review)

1. PC awake, unlocked, signed into Codex. VB-CABLE installed.
2. Telegram: start a new Codex Voice conversation, or name a conversation to resume.
3. Hermes follows the sequence above without a slash command. Status becomes `ready` only from confirm after computer_use Voice and CABLE proof. A UIA ready-name miss must not skip CABLE selection.
4. Play a short non-sensitive phrase into `CABLE Input`. Codex hears it on `CABLE Output`.
5. Telegram: stop Voice. Hermes computer_use ends Voice, then `codex_voice_stop`. Status becomes `inactive`. No delete, cancel, archive, or Codex kill.

## Limits

- One owned Voice session.
- `codex_voice_start` requires `mode=new` or `mode=current` and returns `starting` unless already `ready`.
- `codex_voice_confirm` is the only path to `ready`. Both flags must be true.
- Missing CABLE endpoint fails closed. Unselected CABLE keeps `starting`. The physical PC microphone is never a silent fallback.
- No force-kill of Codex. Stop releases companion state only.
