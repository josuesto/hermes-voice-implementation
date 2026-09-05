# ADR 0002: Browser First, Optional Discord Voice Transport Later

- Status: Sequencing superseded by [ADR 0004](0004-discord-first-direct-audio.md) on 2026-09-04; retained as historical rationale
- Date: 2026-09-01
- Decision owners: project maintainer and Codex planning authority

## Context

The first product flow uses a lightweight phone browser as the microphone and speaker for the real Codex Voice session running on the user's Windows PC. A future flow should let Hermes place that same session into an authorized Discord voice call: Hermes starts or stops the session, a Discord bot joins the call, authorized participant audio is sent to Codex, and only Codex application audio is sent back.

Treating Discord as a second product or duplicating Codex/task/audio logic would create inconsistent lifecycle, security, and cleanup behavior. Making Discord a first-release requirement would also delay the browser path that motivated the project.

Discord is an external platform with evolving voice requirements. Its official documentation currently describes separate Gateway and UDP voice connections, `CONNECT` and `SPEAK` permissions, Opus media, and DAVE end-to-end encryption requirements. Those requirements and any selected community library must be revalidated when this adapter is implemented.

## Decision

1. The browser remains the only required client transport for the first stable release.
2. Discord is a post-v1 optional transport adapter in the same repository and package family.
3. The adapter reuses the production Windows companion, Codex adapter, audio engine, task-selection behavior, session state machine, and Hermes tools. It does not implement a separate agent or voice model.
4. Hermes is the authoritative control surface for start, status, and stop. The Discord bot is not a general chatbot and does not read text-channel content.
5. Each user creates and owns their Discord application and bot token. The project operates no shared Discord bot.
6. Setup requests only the channel visibility/connect/speak capabilities that are actually required. It must not request Administrator or unrelated message permissions.
7. One configured guild and voice channel are allowlisted per active configuration. Speaker identities are explicitly authorized; audio from other participants is discarded before injection unless the owner deliberately changes that policy.
8. Only one client transport may own a host's Codex Voice media session at a time. Browser and Discord audio are not mixed in the first Discord release.
9. The bot has a clear visible identity, and documentation requires disclosure to call participants that authorized live speech is being forwarded to Codex.
10. The adapter stores no call audio or additional transcript. The bot token is held in operating-system-protected credential storage and is excluded from prompts, logs, diagnostics, and source control.
11. Hermes stop, Codex Voice stop, authorization failure, or unrecoverable media failure makes the bot leave the channel, releases audio resources, and preserves the underlying Codex task.
12. The adapter cannot ship until current Discord voice encryption/DAVE support, bidirectional media, self-audio exclusion, reconnect, permission loss, and cleanup pass dedicated checkpoints.

## Consequences

- The browser-first release is not delayed by Discord work.
- Core components need a small transport interface rather than browser assumptions embedded throughout the audio and lifecycle code.
- Discord users gain a call-native endpoint without deploying or opening the phone page for that session.
- The optional adapter depends on Discord availability and policy, while the core browser product remains independent of Discord.
- A maintained DAVE-capable library is strongly preferred; implementing Discord's evolving voice protocol directly would require separate security and maintenance justification.
- Multi-speaker authorization and participant transparency become explicit product responsibilities.

## Deferred decisions

- The implementation language and Discord voice library.
- Whether one installation may configure more than one allowlisted guild/channel while still allowing only one active media session.
- Whether future releases permit a restricted Discord interaction for status only. Hermes remains the required start/stop authority for the first adapter.
- Whether authorized speakers are configured individually, through an allowlisted role, or both.

## References

- [Discord voice connections](https://docs.discord.com/developers/topics/voice-connections)
- [Discord permissions](https://docs.discord.com/developers/topics/permissions)
- [Discord bots and companion apps](https://docs.discord.com/developers/platform/bots)
