# MVP-02 local Hermes Codex Voice control

Development slice for same-host Windows. Cloudflare, remote access, pairing, and Discord stay out of scope. App Server and CP-013 stable-ID resume stay out of scope. Do not touch the preserved CP-013 disposable task.

Hermes `computer_use` owns visible Codex UI. Companion tools own preflight, packaged Codex launch, one audio transport, session state, and cleanup. A Telegram request such as start Codex Voice should load the indexed skill without a slash command.

## Layout

- `skills/hermes_voice/SKILL.md` is the indexed skill source of truth.
- `plugin/hermes_voice/` is the Hermes plugin (`register(ctx)` with `ctx.register_tool`). Its SKILL.md copy must match the indexed file.
- `companion/codex_control.py` is the Windows companion: session lock, packaged Codex activation, unique window proof, endpoint presence, transport ownership, and `starting`/`ready`/`inactive` state.
- `companion/browser_call/` is the loopback WebRTC server and static call page. `companion/process_loopback/` is the Codex process-capture helper. Copying `companion` during plugin install includes both.
- Status values: `inactive`, `starting`, `ready`, `stopping`, `failed`.
- Tool JSON keys: `ok`, `status`, `error` when failed, and `url` only for an active browser transport. The only allowed URL is `http://127.0.0.1:8765/`.

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

Python extras used by physical-mic transport: `soundcard`, `sounddevice`, `numpy`, and `comtypes`. Browser extras are optional and listed in `companion/browser_call/SETUP.md`. Configure one physical source microphone without changing Windows defaults:

```json
{
  "source_microphone": "Exact Windows WASAPI microphone name"
}
```

Save that as `%HERMES_HOME%\config\hermes_voice.json` (normally `%LOCALAPPDATA%\hermes\config\hermes_voice.json`). `HERMES_VOICE_SOURCE_MIC` can override it. The companion requires one exact Windows WASAPI match and never silently falls back to another microphone.

## Tests

Audio spike, companion/plugin/skill fakes, browser-call, and the native helper:

```
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s prototype\windows-bridge\tests -v
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s companion -v
.\prototype\windows-bridge\.venv\Scripts\python.exe -m unittest discover -s prototype\browser-call\tests -v
.\companion\process_loopback\build-helper.ps1
```

## Tool sequence

New:

1. `codex_voice_start` with `mode=new` and `transport=physical_mic` or `transport=browser` returns `starting`.
2. App-scoped `computer_use` creates the fresh conversation.
3. Hermes reads the visible model and effort choices, asks the user, selects and verifies both.
4. App-scoped `computer_use` starts Voice and verifies it is visible.
5. Hermes re-checks both selectors after Voice startup and corrects any automatic change.
6. `codex_voice_confirm` with all three verification flags true returns `ready`. Browser transport includes `url` only then. `CABLE Output (VB-Audio Virtual Cable)` is a one-time Codex Settings choice, not a per-call control.

Resume:

1. `codex_voice_start` with `mode=current` and the inferred transport returns `starting` (launch first when Codex is closed).
2. App-scoped `computer_use` lists up to ten visible names if needed, user chooses duplicates, then verifies the title is selected or open.
3. Hermes reads the visible model and effort choices, asks the user, selects and verifies both.
4. App-scoped `computer_use` starts Voice and verifies Voice.
5. Hermes re-checks both after Voice startup.
6. `codex_voice_confirm` returns `ready` only with `voice_visible=true`, `model_verified=true`, and `effort_verified=true`.

Stop:

1. App-scoped `computer_use` ends Voice and a post-action capture shows it ended.
2. `codex_voice_stop` cooperatively stops the owned transport and returns `inactive`. The Codex task remains open.

## Acceptance result — 2026-09-02

Accepted on the reference PC. A real Telegram request caused Hermes to follow the task flow, ask for model and effort, start real Codex Voice, and automatically route the configured Blue Snowball into VB-CABLE; the user confirmed Codex heard the routed speech. The installed companion also passed a direct start/status/stop lifecycle check. The owner intentionally declined a redundant Telegram stop-click check; that visible orchestration remains unexercised but is not an MVP blocker under the risk-based review policy.

Acceptance procedure:

1. PC awake, unlocked, signed into Codex. VB-CABLE installed.
2. Telegram: start a new Codex Voice conversation, or name a conversation to resume.
3. Hermes follows the sequence above without a slash command, asks for model and effort, and status becomes `ready` only after post-Voice verification.
4. Speak a short non-sensitive phrase into the configured physical microphone. The companion routes it into `CABLE Input`, and Codex hears it on `CABLE Output`.
5. Telegram: stop Voice. Hermes computer_use ends Voice, then `codex_voice_stop`. Status becomes `inactive`. No delete, cancel, archive, or Codex kill.

## Limits

- One owned Voice session.
- `codex_voice_start` requires `mode` and `transport`. Same-transport start may be idempotent. Switching transport while `starting` or `ready` fails until stop.
- `codex_voice_confirm` is the only path to `ready`. Voice, model, and effort verification flags must all be true.
- Each start requires an explicit model and effort choice. Hermes discovers visible options rather than hardcoding them and re-checks both after Voice starts.
- Missing CABLE endpoints or missing configured physical source fail closed. Codex must be configured once to use CABLE Output; the runtime does not try to change that setting.
- Browser extras missing return `browser_dependency_missing` without breaking physical-mic loading.
- No force-kill of Codex. Stop releases companion state and the owned transport only.
