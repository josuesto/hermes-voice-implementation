# Windows audio spike (MVP-01)

This prototype proves local playback and WASAPI loopback on this PC. It does not record audio. It does not change Windows default devices. It does not start Codex Voice by itself.

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

Codex desktop on this PC is the store-signed `OpenAI.Codex` package. Open it from the Start menu as ChatGPT or Codex. Create a **fresh** task. Click Voice manually. Do not open, rename, archive, or inspect the preserved CP-013 test task. Existing-task resume is out of scope.

## Current limitation

Windows cannot inject PCM into a physical microphone. A two-way Voice path needs a virtual cable: a playback sink that forwards into a capture source Codex can select as its microphone.

This machine currently has no such endpoint. The spike can play a test tone and monitor system output through WASAPI loopback. It cannot feed audio into Codex Voice until a virtual cable is installed.

## Missing dependency (do not install yet)

Exact option: **VB-CABLE Virtual Audio Device** from VB-Audio.

- Official source: https://vb-audio.com/Cable/
- Licensing terms: https://vb-audio.com/Services/licensing.htm
- Current Windows package named on the product page as of 2026-09-01: `VBCABLE_Driver_Pack45.zip` (OCT 2024, XP through Win11, 32/64-bit and Arm64)
- License: donationware. Personal install from the official site is allowed. Professional, company, or institutional use requires a paid license. Server use is not independently a license trigger in those terms.
- This MVP does not redistribute or bundle VB-CABLE. Users install it from the official source. VB-Audio permits distributing the standard VB-CABLE package under stated donationware conditions; this project chooses not to. VB-CABLE A+B and C+D have different distribution rules and are out of scope.
- Admin: required. Run the setup EXE as administrator after extracting the zip to a local folder. Do not run setup from inside the zip.
- Restart: required after install and after uninstall.
- Topology after install: `CABLE Input` is the playback sink; `CABLE Output` is the capture source Codex Voice can use.

Do not download mirrors. Do not install until the user approves this exact package.

## What this spike will not do

- Save wav, mp3, or any audio file
- Change or restore Windows default devices (it never changes them)
- Automate the Codex Voice button
- Resume or mutate an existing Codex task
- Install drivers, Cloudflare, Hermes, Discord, or browser pieces
