# MVP-03 local browser transport

This is a one-peer WebRTC spike, not a release server. It sends browser microphone audio to standard VB-CABLE `CABLE Input` in memory. The return track captures only the unique current-session Codex process tree through Windows process loopback. It does not capture endpoint-wide system audio. An explicit one-second 440 Hz return-path tone remains available for transport diagnosis.

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
- Mute Codex audio: mutes browser playback without stopping process capture.
- Test return audio: asks the server to emit a one-second tone through the WebRTC return track.
- End session: closes the peer and releases CABLE Input without touching Codex.

## Native helper

The server builds `../process-loopback/ProcessLoopbackCapture.cs` on demand with Windows' included C# compiler. The owned child streams 48 kHz stereo PCM through a pipe; a two-second in-memory queue bounds latency and memory. Closing the call cooperatively stops the child, with termination reserved for that exact owned child if it does not exit promptly. Generated binaries are ignored.

## Remaining before a phone trial

The local two-way transport still needs one live browser-to-Codex-to-browser conversation test. A phone then needs browser-trusted HTTPS plus pairing/authentication; this unauthenticated localhost spike must not be exposed publicly.
