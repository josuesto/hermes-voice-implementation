# MVP-03A local browser transport

This is a one-peer WebRTC spike, not a release server. It sends browser microphone audio to standard VB-CABLE `CABLE Input` in memory. Its outgoing track is silence except for an explicit one-second 440 Hz return-path test. It does **not** yet capture Codex audio; MVP-03B must replace the test track with Windows process-tree loopback scoped to `chatgpt.exe` before the product can claim a two-way Codex call.

No audio, SDP, ICE payload, address, prompt, transcript, or task content is logged or saved. One peer is allowed. HTTP binds to `127.0.0.1` by default. Non-loopback binding is refused without a certificate and key. There is no pairing or session authentication yet, so do not expose this prototype to the public internet.

## Run locally

```powershell
.\prototype\windows-bridge\.venv\Scripts\python.exe -m pip install -r prototype\browser-call\requirements.txt
.\prototype\windows-bridge\.venv\Scripts\python.exe prototype\browser-call\server.py
```

Open `http://127.0.0.1:8765`. Loopback origins are treated as secure contexts by current browsers. A phone needs browser-trusted HTTPS; that test follows after local desktop negotiation passes.

## Controls

- Start call: requests microphone access and creates one WebRTC peer.
- Mute microphone: disables the browser audio track.
- Mute Codex audio: mutes browser playback. During MVP-03A the outgoing track is only silence/test tone.
- Test return audio: asks the server to emit a one-second tone through the WebRTC return track.
- End session: closes the peer and releases CABLE Input without touching Codex.

## Required next slice

Implement Microsoft `AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK` with `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`, target the uniquely identified current-session Codex process tree, stream PCM directly into the outgoing WebRTC track, and fail closed rather than falling back to system loopback.
