# Codex process-loopback helper

This Windows-only helper captures PCM rendered by one process and its child process tree. Hermes Voice targets the unique current-session Codex main window, so browser callers receive Codex audio without receiving unrelated system audio.

It uses Microsoft's documented `ActivateAudioInterfaceAsync` process-loopback API with `AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK` and `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`. It never falls back to endpoint-wide loopback and never writes captured audio to disk.

The source is compiled on the user's PC with the C# compiler included in current Windows installations. Generated binaries live under an ignored `build/` directory.

```powershell
.\prototype\process-loopback\build-helper.ps1
```

Raw mode writes a fixed 12-byte `HVPC` format header followed by 48 kHz, stereo, signed 16-bit little-endian PCM to standard output. Closing its standard input requests cooperative shutdown. Meter mode observes only in memory and returns an amplitude bucket; it does not return or save samples.

Minimum supported operating system for this route is Windows 10 build 20348. The implementation follows the public API contract and was informed by Microsoft's [Application Loopback sample](https://github.com/microsoft/Windows-classic-samples/tree/main/Samples/ApplicationLoopback).
