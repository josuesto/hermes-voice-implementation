# Threat model v0

Version: v0
Date: 2026-09-01
Checkpoint: CP-003
Status: **security baseline; controls not yet implemented**

Related: [data-flow v0](data-flow-v0.md), [ADR 0001](../adr/0001-user-owned-infrastructure-no-mandatory-shared-service.md), [product plan](../plan.md), [checkpoint map](../checkpoint-map.md)

This document is architecture input for Phase Zero feasibility work. It is not a security certification, penetration-test report, or claim that any control exists in running software. Every control named here is **planned**, **required**, **proposed**, or **to be validated** unless an item is explicitly labeled a present-day trust assumption.

## 1. Status and review boundary

### In scope

- Planned same-host topology: Hermes agent/gateway and Codex desktop on one awake, unlocked Windows user session, with a planned Windows companion as the local authority.
- Planned remote media path from a paired phone browser through a user-owned provider endpoint, STUN, and TURN.
- Planned local IPC, Codex adapter, audio engine, pairing, session authorization, logging, diagnostics, and update trust.
- Deferred separate-host Hermes as a later design boundary that must not be ignored.

### Out of scope

- Waking, unlocking, or controlling Windows while locked or powered off.
- Defending a fully compromised unlocked Windows user session as if the bridge could fully contain it.
- Replacing OpenAI, Telegram, Cloudflare, or Windows authentication.
- Claiming a specific Cloudflare Workers, Tunnel, or TURN product architecture is frozen.
- Production implementation, CI, packaging, or any working companion, plugin, page, or provider adapter.
- Private machine inventory from CP-002.

## 2. Security and privacy objectives

- Only the authorized Hermes owner can request session preparation.
- A phone URL alone never authorizes access.
- A paired phone can join only a session Hermes has activated.
- The phone cannot wake or unlock Windows or silently start Codex.
- The correct Codex task must be verified before Voice or audio attachment.
- Phone audio reaches only the selected Codex microphone path.
- Captured output contains only Codex audio, not system-wide audio.
- The bridge intentionally stores no audio, added transcript, prompt, model response, or task content.
- Ending the remote media/Voice session preserves the underlying Codex task.
- Secrets remain inside their native trust boundary.
- All dangerous or ambiguous states fail closed.

## 3. Assets and classification

| Asset | Owner | Sensitivity | Allowed locations | Permitted lifetime | Prohibited destinations | Planned protection |
|---|---|---|---|---|---|---|
| OpenAI/Codex authenticated session | User / OpenAI, held by Codex desktop | Credential/secret | Codex desktop process and its native account store | Until the user signs out or the session expires | Hermes prompts, companion logs, phone page, provider, Telegram | Companion never reads OpenAI credentials. Control stays inside the interactive Windows user session. |
| Telegram bot/transport authorization | User / Hermes configuration | Credential/secret | Hermes native config/store | Until rotated or revoked | Companion logs, phone, provider, Codex prompts | Inherited Hermes owner policy. Plugin does not duplicate or extract Telegram credentials. |
| Provider OAuth/API credentials | User / provider | Credential/secret | Windows Credential Manager or equivalent OS-protected store | Until rotated, expired, or uninstalled | Prompts, logs, phone storage, Telegram | Planned OS-protected storage. Preview and explicit approval before billable use. |
| Windows user session and local IPC secret | User / planned companion | Credential/secret | Per-user companion process and ACL-protected secret store | Installation lifetime unless rotated | Network, phone, provider, Telegram | Planned named pipe or loopback IPC with per-user ACLs plus an installation-specific secret, to be chosen and tested later. |
| Phone device private key | Phone browser/device | Credential/secret | Phone-local secure storage | Until the user clears storage or revokes the device | Host disk, logs, Telegram, provider control plane | Planned non-extractable or OS-backed storage where available. Host stores only the public key. |
| Registered device public key and trust record | Planned companion | Sensitive metadata | Host device store | Until expiry, revocation, or uninstall | Logs as raw key material, Telegram, provider | Planned public-key record with friendly label, timestamps, and expiry. |
| Pairing codes | Planned companion | Credential/secret | Ephemeral host memory and the owner channel that delivers the code | Seconds to minutes, short-lived | Logs, diagnostics, durable provider storage | Planned one-time code, rate limiting, lockout. |
| Session identifiers/challenges | Planned companion and phone | Sensitive metadata | Ephemeral session state | Active session plus reconnect grace | Logs as reusable secrets, durable storage after End Session | Planned host/session/device binding, signed challenge, invalidation on end. |
| TURN credentials | Planned companion / user-owned TURN | Credential/secret | Ephemeral session use only | Short-lived and session-scoped | Logs, diagnostics, phone durable storage | Planned minting of short-lived credentials; invalidate on End Session. |
| Codex task identity and recent-task metadata | Planned companion, derived from Codex | Sensitive metadata | Companion memory and Hermes tool responses | Session/list lifetime | Audio path, provider media, unredacted public logs | Planned stable IDs where available; titles only when needed and redacted in diagnostics. |
| Phone microphone audio | Phone user | Sensitive content | In-memory WebRTC and planned audio engine buffers | Ephemeral, not persisted | Disk, logs, transcripts, provider control plane, Telegram | Planned DTLS-SRTP; no bridge recording. |
| Codex output audio | Codex desktop / user | Sensitive content | In-memory process capture and WebRTC | Ephemeral, not persisted | System-wide capture path, disk, logs | Planned process-specific capture; no silent system-wide fallback. |
| Operational logs and diagnostic bundles | Planned companion | Operational metadata | Local log store after future privacy filter | Future bounded retention policy | Content, secrets, addresses, exact personal paths | Planned allowlist/denylist. Local preview and scrub before sharing. |
| Installation/update artifacts and signing keys | Project maintainers; user verifies | Public artifact plus signing secret | Release channel; signing keys remain maintainer-held | Release lifetime | Unsigned binaries treated as trusted | Planned signed/checksummed artifacts and a future release-key policy. **Not implemented yet.** |

## 4. Threat actors and capabilities

| Actor | Capabilities | Notes |
|---|---|---|
| Random internet user who discovers the URL | Fetch the page URL, attempt signaling, attempt pairing-code guessing | URL knowledge is not authorization. |
| Attacker replaying a pairing/session message | Capture and resend prior pairing or join messages | Planned short-lived codes, signed challenges, and invalidation. |
| Stolen or malicious paired phone | Use a still-trusted device key until expiry or revocation | Can join only an already activated session. Cannot start Codex. Revocation is required. |
| Compromised Telegram account or unauthorized Telegram participant | Send Hermes messages if owner policy is misconfigured | Inherited Hermes owner authorization. Fail closed if owner identity is unreliable. |
| Compromised provider account/control plane | Change hostname, signaling, STUN/TURN, or inspect metadata the provider can see | Provider sees routing metadata, not decoded media if DTLS-SRTP holds. User-owned account. |
| Malicious or compromised user-level local process | Talk to local IPC if ACLs/secret fail; observe same-user audio APIs | Residual risk inside the Windows user session. |
| Network observer or hostile NAT/Wi-Fi | Observe IPs, block UDP, attempt TLS downgrade, inspect TURN packets | Planned TLS and DTLS-SRTP. Direct path may leak candidate addresses to STUN. |
| Compromised separate-host Hermes node | Issue forged companion RPCs if node pairing is weak | Deferred topology. Planned node keys, narrow RPC, replay protection, revocation. |
| Malicious dependency or update artifact | Supply trojaned companion, driver, or page assets | Planned signatures/checksums. **Not implemented yet.** |
| Accidental operator error, stale session, or wrong-task selection | Start Voice on the wrong task or leave a metered session running | Planned act-and-verify task identity, busy handling, and abandoned-session cleanup. |

A fully compromised unlocked Windows user session is a **trust assumption and residual risk**. The bridge cannot fully defend Codex, local audio, or OS-protected secrets against malware running as that same user.

## 5. Trust boundaries and planned authentication matrix

| Boundary | Initiator | Receiver | Data | Planned authentication | Confidentiality / integrity | Authorization owner | Replay control | Failure behavior |
|---|---|---|---|---|---|---|---|---|
| Telegram owner to Hermes | Telegram user/client | Hermes agent/gateway via Telegram service | Owner commands, status text, current page link | Inherited Hermes owner policy. Plugin does not extract Telegram credentials. | Telegram transport TLS as provided by that service | Hermes owner configuration | Hermes/Telegram native anti-replay where present; companion still requires a fresh session | If owner identity is unreliable, session activation is **required** to be disabled. |
| Hermes to same-host companion | Hermes agent/gateway | Windows companion | Narrow tool calls: setup/status/task/Voice/session/device/diagnostics | Planned named pipe or loopback IPC with per-user ACLs plus installation-specific secret, to be chosen/tested later | Local OS isolation; secret not logged | Companion is local authority | Planned command IDs / idempotency | Unauthenticated local clients are rejected. |
| Deferred separate-host Hermes to companion | Remote Hermes node | Windows companion | Same narrow RPC set | Planned node identity keys, pairing, request signing | Encrypted control channel through the user-owned meeting point | Companion remains local authority | Planned replay protection and stale-command rejection | Revoked or unknown nodes fail closed. **Deferred.** |
| Companion/Codex adapter to Codex desktop | Codex adapter | Codex desktop | Launch, task select/verify, Voice start/stop, state observation | Interactive Windows user session. No OpenAI credential read. | Stays on the local desktop; no extra network credential | Companion after task verification | Stale UI actions must not attach Voice to the wrong task | Unknown version or missing verify signal: fail closed. |
| Companion to provider control plane | Companion | User-owned provider endpoint | Hostname, route start/stop, STUN, short-lived TURN minting | Planned provider OAuth/API using OS-protected secrets | TLS to provider APIs | User approval for creation/billing | Provider token refresh; no long-lived TURN | Missing auth or failed health check: do not publish a joinable session. |
| Phone browser to page/signaling endpoint | Phone browser | User-owned HTTPS page/signaling | Page assets, signaling messages | TLS server authenticity. Page load is not session authorization. | TLS | Companion/session layer, not the URL | Signaling messages still require device/session auth | Inactive route or TLS failure: page unavailable. |
| Phone browser to active companion session | Phone browser | Companion session auth | Device proof, join/reconnect, call control | Planned device-key pairing, short-lived signed challenge, host/session/device binding, expiry, rate limiting, revocation | TLS signaling plus later media crypto | Companion: join allowed only after Hermes-activated session | Fresh challenge each join/reconnect; pairing codes one-time | Unpaired, expired, revoked, or no active session: fail closed. |
| WebRTC direct path | Phone browser and companion | Each other, assisted by STUN | Encrypted media | DTLS-SRTP after authenticated signaling | DTLS-SRTP. STUN does not authenticate the user. | Companion session | ICE is not an auth substitute | Direct failure proceeds to configured TURN or errors. |
| TURN-relayed path | Phone browser and companion | User-owned TURN | Encrypted media packets | Short-lived TURN credentials plus DTLS-SRTP | DTLS-SRTP. TURN is not granted decoded audio. | Companion session | Credential expiry and End Session invalidation | Stolen/expired TURN credentials fail. |
| Companion/update installer to update source | Installer/updater | Public repository/release channel | Artifacts, manifests, checksums | Planned signed/checksummed artifacts and future release-key policy | TLS plus signatures | User/installer verification | Reject unsigned or mismatched artifacts | **Explicitly not implemented yet.** Fail closed when policy exists. |

## 6. Abuse cases, controls, and residual risks

| ID | Scenario | Affected assets | Preventive controls | Detective controls | Recovery / revocation | Residual risk | Owning later checkpoint |
|---|---|---|---|---|---|---|---|
| AC-01 | URL leakage | Page/signaling endpoint | URL is not a secret. Device pairing and session auth are required. | Failed join without device proof | No credential rotation required for URL disclosure alone | Page existence may be observable | CP-044, CP-122, CP-150 |
| AC-02 | Pairing brute force | Pairing codes, device trust | Short-lived codes, rate limiting, lockout | Repeated failure counts | Invalidate code; require new pairing | Stolen owner channel that delivers the code | CP-044, CP-122 |
| AC-03 | Replay of pairing or join | Session identifiers, pairing codes | One-time codes, signed fresh challenges | Replay rejected as stale | Rotate challenge; end session | Capture of a still-valid unused code | CP-044, CP-123 |
| AC-04 | Stolen or malicious paired phone | Device private key, live media | Join only Hermes-activated sessions; phone cannot start Codex; trust expiry | Unexpected join/device list | Immediate device revocation | Until revocation, a trusted stolen phone can join an active session | CP-044, CP-122 |
| AC-05 | Compromised provider account | Hostname, signaling, TURN | User-owned account; explicit billing preview; short-lived TURN | Provider health/anomaly | Revoke provider credentials; stop route | Provider metadata and availability | CP-040, CP-046, CP-150 |
| AC-06 | Forged Hermes request | Companion control, Codex Voice | Same-host IPC secret/ACLs; deferred node signing | Unauthorized IPC/RPC rejected | Rotate IPC/node secrets | Compromised owner Telegram if Hermes policy is wrong | CP-102, CP-140, CP-114 |
| AC-07 | Malicious local process | IPC secret, audio, Codex session | Per-user ACLs, installation secret, fail closed | Unexpected local clients | Rotate IPC secret; stop companion | Same-user malware is residual | CP-102, CP-150 |
| AC-08 | Task confusion / wrong task | Codex task identity, audio | Act-and-verify stable task identity before Voice | Mismatch fails before audio | Stop Voice without cancelling task | Duplicate titles without stable IDs | CP-012, CP-013, CP-016 |
| AC-09 | System-audio leakage | Unrelated application audio | Process-specific capture only; no silent system-wide fallback | Isolation tests | Stop capture; fail the session | Adapter bugs under process-tree changes | CP-022, CP-024, CP-026 |
| AC-10 | Silent PC-microphone fallback | Physical PC microphone | Pin virtual/phone path; never substitute physical mic | Device-pin assertions | Error and stop injection | Driver or OS default mutation | CP-021, CP-024 |
| AC-11 | Abandoned metered Voice session | Codex Voice, TURN usage | Timeouts, orphan detection, End Session cleanup | Cleanup-state evidence | Stop Voice and invalidate session/TURN without deleting the task | Until timeout, metered Voice may continue | CP-014, CP-045, CP-117 |
| AC-12 | TURN credential theft | TURN credentials, media packets | Short-lived, session-scoped credentials; DTLS-SRTP | Expired/revoked credential failures | Invalidate on end; remint | Brief relay of ciphertext if credentials leak while valid | CP-043, CP-123 |
| AC-13 | Update tampering | Install/update artifacts | Planned signatures/checksums; **not implemented yet** | Signature mismatch | Refuse install; restore last known signed artifact | Supply chain until CP-154 | CP-134, CP-154 |
| AC-14 | Logs leaking content | Prompts, transcripts, audio, secrets | Allowlist logging; denylist content/secrets | Privacy filter on diagnostics | Delete/scrub bundle | Regex filters miss novel secret shapes | CP-104, CP-153 |
| AC-15 | Windows locking mid-call | Windows session, audio, Codex UI | Product requires awake unlocked session; no unlock automation | Detect lock/unsupported state | Fail closed; do not attempt unlock | Call ends; task should remain | CP-011, CP-025, CP-151 |

## 7. Frozen privacy invariants

These rules are normative.

1. The bridge MUST NOT record audio or add a transcript.
2. Logs and diagnostics MUST NOT contain audio, prompts, task content, Codex responses, or transcripts.
3. Logs, prompts, and skill text MUST NOT contain OpenAI, Telegram, provider, Windows, or device private credentials.
4. Knowledge of the page URL MUST NOT be sufficient for access.
5. The phone page MUST NOT activate Codex or start the bridge by itself.
6. The companion MUST NOT silently fall back to the physical PC microphone.
7. The companion MUST NOT silently fall back to system-wide audio capture.
8. End Session MUST NOT cancel, close, archive, or delete the underlying Codex task.
9. The project MUST NOT operate a mandatory shared control plane, signaling service, or media relay.
10. The product MUST NOT create a billable provider resource without explicit preview and approval.

## 8. Logging and diagnostics policy

Telemetry is off by default. Any future telemetry requires explicit opt-in.

**Allowlist (operational metadata):** component and schema version; coarse timestamps and durations; lifecycle state names; sanitized error categories; browser family and capability result; ICE candidate class without addresses; cleanup result; non-identifying device label.

**Denylist:** exact filesystem paths; IP and MAC addresses; usernames; task titles unless deliberately redacted; raw command output; SDP and ICE payloads; tokens and credentials; audio; transcripts; prompts; model responses; Telegram bot details.

Diagnostic bundles are **planned** to be generated locally, previewed, and scrubbed before a user shares them.

## 9. Assumptions, limitations, and deferred validation

| Topic | Assumption or gap | Later owner |
|---|---|---|
| Evidence harness and sanitized results | No implementation proof yet | CP-004 |
| Codex discovery, launch, task identity, Voice state | Planned adapter; unofficial desktop surface | CP-010 through CP-016 |
| Virtual microphone, capture isolation, recovery | Planned audio engine | CP-020 through CP-026 |
| Phone browser capabilities and interruptions | Capability-based floor; foreground/screen-awake baseline | CP-030 through CP-035 |
| Provider contract, HTTPS route, STUN, TURN, pairing, roaming | User-owned Cloudflare is the intended first candidate, unfrozen mechanism | CP-040 through CP-046 |
| Adversarial security suite | After separate-host qualification | CP-150 |
| User documentation and sanitized diagnostics | After compatibility freeze | CP-153 |
| Signing, SBOM, licenses | Before release candidate | CP-154 |
| Unlocked Windows session | Fully compromised same-user malware is outside the bridge's ability to fully defend | Residual risk, not a later “fix the OS” claim |

## 10. Review checklist (CP-003 pass criteria)

- [ ] Every process and network boundary has a named planned authentication method or is explicitly deferred/out of scope. See section 5.
- [ ] Required assets are listed with owner, sensitivity, location, lifetime, and protection. See section 3.
- [ ] Required threat actors are covered, including residual Windows-session risk. See section 4.
- [ ] Required abuse cases are traced to controls and later checkpoints. See section 6.
- [ ] Frozen privacy invariants use MUST/MUST NOT language. See section 7.
- [ ] Media confidentiality has a named control (TLS + DTLS-SRTP) and later owners CP-042/CP-043/CP-150.
- [ ] Device revocation has a named control and later owners CP-044/CP-122.
- [ ] Provider-secret storage has a named control (OS-protected store) and later owners CP-040/CP-121.
- [ ] Local IPC has a named planned control and later owner CP-102.
- [ ] Software-update trust has a named planned control and later owner CP-154, explicitly not implemented yet.
- [ ] Data-flow document distinguishes control, signaling, direct media, relay media, persistence, and deletion. See [data-flow v0](data-flow-v0.md).
- [ ] Owner authorization fails closed if Hermes cannot identify the owner. See [data-flow v0](data-flow-v0.md) section 6.
- [ ] ADR 0001 preserves user-owned infrastructure without freezing an untested provider mechanism. See [ADR 0001](../adr/0001-user-owned-infrastructure-no-mandatory-shared-service.md).
- [ ] Documents make no false implementation claims and copy no private CP-002 evidence.
