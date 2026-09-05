# ADR 0004: Discord first, direct audio only

Status: accepted owner direction; implementation pending.
Date: 2026-09-04.

The owner resumed the project with Discord as the next call endpoint and explicitly declined transcription. This supersedes ADR 0002's browser-first/post-v1 sequencing, not its user-owned bot, minimum-permission, task-preservation, and no-recording boundaries.

The next implementation is [MVP-D01](../mvp-d01-discord-voice.md): one private guild voice channel carries the owner's speech into the actual Windows Codex Voice microphone and sends only Codex application audio back. Hermes remains the controller for new/current conversation selection, model/effort verification, start, and stop. Natural-language aliases are "summon Codex" and "dismiss Codex"; existing tool names remain stable.

Keep browser code and its unfinished acceptance test. Browser HTTPS, Cloudflare, pairing, general compatibility, separate-host Hermes, and CP-013 research do not block the Discord slice. No speech-to-text, transcripts, TTS, replacement model, or required paid transcription provider is added. Discord remains a third-party service, but each owner runs their own bot and PC bridge; this project hosts no shared service.

The development bot credential may be supplied privately through the companion's process environment. Never include it in prompts, logs, command arguments, or Git. Protected credential-store onboarding remains a packaging requirement. Only the owner and bot may participate in the first private-channel test; additional participants pause both media directions instead of silently gaining access to Codex's replies.

Brief owner absence pauses media while keeping the session available. Confirmation uncertainty or a Hermes turn ending does not imply stop. Authorization failure or unrecoverable media failure releases owned media and reports failure without cancelling the Codex task. Explicit owner stop uses Hermes computer use to end Voice, then tears down the transport. This distinction updates ADR 0002's broad stop-on-failure wording.

Execution stays one Grok 4.6 implementation pass, one short Codex risk-based review, and a real two-way call. The pivot is not evidence that Discord receive, phone compatibility, or Windows audio already works.
