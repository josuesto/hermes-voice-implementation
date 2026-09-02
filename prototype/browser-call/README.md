# MVP-03 local browser transport

Development wrapper. The WebRTC server, static call page, and process-loopback helper live in `companion/browser_call/` and `companion/process_loopback/`. Copying `companion` during plugin install includes that runtime.

This is a one-peer WebRTC slice, not a release server. Browser microphone audio goes to standard VB-CABLE `CABLE Input` in memory. The return track captures only the unique current-session Codex process tree. Leave call closes the WebRTC peer only. Hermes `codex_voice_stop` stops the owned server.

```powershell
.\prototype\windows-bridge\.venv\Scripts\python.exe -m pip install -r companion\browser_call\requirements.txt
.\prototype\windows-bridge\.venv\Scripts\python.exe prototype\browser-call\server.py
```

Open `http://127.0.0.1:8765`. Loopback origins are treated as secure contexts by current browsers. Do not expose this unauthenticated page beyond loopback.
