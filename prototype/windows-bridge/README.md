# Windows audio spike (MVP-01)

This prototype proves local playback, WASAPI loopback, the installed VB-CABLE route, and bounded physical-microphone forwarding on the reference PC. It does not record audio. It does not change Windows default devices. It does not start Codex Voice by itself; Hermes controls Codex and Voice.

Python 3.13 via `py -3` is the runtime. Do not use the Hermes agent venv.

## Setup

From this directory:

```
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Commands

List endpoints with names on the console only:

```
.\.venv\Scripts\python.exe bridge.py list
```

List without names, for private notes:

```
.\.venv\Scripts\python.exe bridge.py list --sanitize
```

Play a short 440 Hz tone to the default playback device:

```
.\.venv\Scripts\python.exe bridge.py play --seconds 0.8
```

Play the tone while monitoring system-output loopback in memory:

```
.\.venv\Scripts\python.exe bridge.py spike --seconds 1.0
```

Forward a physical microphone to `CABLE Input` for a bounded local test. Use a physical capture index from `list`; never choose a loopback or `CABLE Output` row. The route uses one continuous low-latency WASAPI callback stream so speech is not fragmented between separate record/play operations:

```
.\.venv\Scripts\python.exe bridge.py route-mic --source 7 --seconds 15
```

During the bounded run, Codex Voice reads the forwarded signal from `CABLE Output`. The command prints only a peak value and forwarded-frame count; it never saves audio.

Start a bounded in-process loopback monitor. There is no background process and no PID kill:

```
.\.venv\Scripts\python.exe bridge.py start --seconds 2
.\.venv\Scripts\python.exe bridge.py status
.\.venv\Scripts\python.exe bridge.py stop
.\.venv\Scripts\python.exe bridge.py restore
```

`stop` writes a cooperative stop marker and waits briefly. If a monitor does not exit, it reports failure and leaves the process alone.

Tests:

```
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Private machine notes belong in the gitignored `work/mvp-01/` directory at the repo root. Do not copy endpoint names, device IDs, prompts, or audio into git.

## Codex Voice

Codex desktop on the reference PC is the store-signed `OpenAI.Codex` package. Runtime startup must be performed by Hermes: launch Codex if needed, create a **fresh** task, start Voice, and verify that Voice is ready. Manual clicking is allowed during installation diagnostics only, not as the normal session flow. Do not open, rename, archive, or inspect the preserved CP-013 test task. Existing-task resume is out of scope.

## Proven virtual-audio route

Windows cannot inject PCM into a physical microphone, so the reference PC uses VB-CABLE. `CABLE Input` is the programmatic playback sink and `CABLE Output` is the capture endpoint that Codex Voice must use as its microphone. Selecting `CABLE Output` in Codex does not automatically route a physical microphone into it: the bridge must forward the chosen microphone into `CABLE Input`. All forwarding is in memory.

## External dependency

Exact option: **VB-CABLE Virtual Audio Device** from VB-Audio.

- Official source: https://vb-audio.com/Cable/
- Licensing terms: https://vb-audio.com/Services/licensing.htm
- Current Windows package named on the product page as of 2026-09-01: `VBCABLE_Driver_Pack45.zip` (OCT 2024, XP through Win11, 32/64-bit and Arm64)
- License: donationware. Personal install from the official site is allowed. Professional, company, or institutional use requires a paid license. Server use is not independently a license trigger in those terms.
- This MVP does not redistribute or bundle VB-CABLE. Users install it from the official source. VB-Audio permits distributing the standard VB-CABLE package under stated donationware conditions; this project chooses not to. VB-CABLE A+B and C+D have different distribution rules and are out of scope.
- Admin: required. Run the setup EXE as administrator after extracting the zip to a local folder. Do not run setup from inside the zip.
- Restart: required after install and after uninstall.
- Topology after install: `CABLE Input` is the playback sink; `CABLE Output` is the capture source Codex Voice can use.

Do not download mirrors. Installation requires the user's approval of the exact package. The reference PC installation was separately approved, completed, restarted, and verified; the project still does not redistribute the driver.

## What this spike will not do

- Save wav, mp3, or any audio file
- Change or restore Windows default devices (it never changes them)
- Automate the Codex Voice button
- Resume or mutate an existing Codex task
- Install drivers, Cloudflare, Hermes, Discord, or browser pieces
