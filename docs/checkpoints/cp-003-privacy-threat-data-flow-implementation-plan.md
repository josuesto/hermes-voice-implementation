# CP-003 Implementation Plan — Privacy, Threat Boundaries, and Data Flow

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-003**  
Scope: Security and privacy documentation only; no networking, credentials, application control, or product implementation

## Objective

Create the first reviewable security baseline for Hermes Voice Implementation before any public endpoint, pairing mechanism, local control API, provider adapter, or media bridge is built. The artifacts must describe what every component may see, store, transmit, and trust; identify threats and controls; freeze privacy invariants; and make unimplemented controls unmistakably prospective rather than claiming they already exist.

## Working locations

Public documentation repository: the repository root containing this plan.

Canonical planning sources:

- [`docs/plan.md`](../plan.md)
- [`docs/checkpoint-map.md`](../checkpoint-map.md)
- CP-002 inventory: private maintainer evidence, not included in Git.

The CP-002 inventory is private supporting context. Do not copy its machine-specific values or paths into the public repository.

## Mandatory boundaries

- Edit only the files explicitly listed in this plan.
- Do not run Codex, Hermes, Telegram, Cloudflare, browser, audio, network, registry, credential, or provider commands.
- Do not contact external services or create provider resources.
- Do not inspect or print credentials, tokens, cookies, provider configuration, Telegram configuration, browser storage, prompts, tasks, transcripts, or audio.
- Do not add product code, dependencies, CI, executable scripts, deployment configuration, or source scaffolding.
- Do not commit or push. Codex will independently review the checkpoint and will commit/push only after acceptance.
- Do not mark CP-003 complete or change checkpoint statuses.
- Describe every future security mechanism as **planned**, **required**, **proposed**, or **to be validated**. Nothing in this checkpoint proves that an implementation exists.
- The public documents must contain no personal paths, machine identifiers, account details, IP/MAC addresses, phone numbers, secrets, or private CP-002 evidence filenames.

## Files to create

In the public repository:

1. `docs/security/threat-model-v0.md`
2. `docs/security/data-flow-v0.md`
3. `docs/adr/0001-user-owned-infrastructure-no-mandatory-shared-service.md`

Private worker report, ignored by Git:

4. `work/cp-003-worker-report.md`

Do not modify `README.md`, `docs\plan.md`, `docs\checkpoint-map.md`, `CONTRIBUTING.md`, `SECURITY.md`, or any other repository file during worker implementation.

## Shared terminology and scope

Use these component names consistently:

- **Telegram user/client** — the user's Telegram interface.
- **Telegram service** — the third-party message transport Hermes already uses.
- **Hermes agent/gateway** — interprets the owner request and invokes narrow companion operations.
- **Windows companion** — planned per-user authoritative local controller on the unlocked Codex PC.
- **Codex desktop** — the user's real signed-in Codex desktop session.
- **Codex adapter** — planned deterministic task/Voice-control boundary inside the companion.
- **Audio engine** — planned phone-mic injection and Codex-only output capture.
- **Phone browser** — paired mobile browser running the call page.
- **User-owned provider endpoint** — page/signaling/tunnel resources in the user's account.
- **STUN service** — assists direct WebRTC candidate discovery; it does not authenticate the user.
- **TURN service** — relays encrypted WebRTC packets when a direct path fails.
- **Update source** — the public repository/release channel and future signed artifacts.

Initial implemented topology is not claimed. The first intended topology is same-host Hermes and Codex on one awake, unlocked Windows user session. Separate-host Hermes is a later design boundary that must still be represented and labeled deferred.

## Artifact 1 — `threat-model-v0.md`

Use this structure.

### 1. Status and review boundary

- Title, version `v0`, date, checkpoint, and status: **security baseline; controls not yet implemented**.
- State that the document is architecture input for feasibility work, not a security certification.
- Name what is in scope and explicitly out of scope.

### 2. Security and privacy objectives

At minimum:

- Only the authorized Hermes owner can request session preparation.
- A phone URL alone never authorizes access.
- A paired phone can join only a session Hermes has activated.
- The phone cannot wake/unlock Windows or silently start Codex.
- The correct Codex task must be verified before Voice/audio attachment.
- Phone audio reaches only the selected Codex microphone path.
- Captured output contains only Codex audio, not system-wide audio.
- The bridge intentionally stores no audio, added transcript, prompt, model response, or task content.
- Ending the remote media/Voice session preserves the underlying Codex task.
- Secrets remain inside their native trust boundary.
- All dangerous or ambiguous states fail closed.

### 3. Assets and classification

Create a table with asset, owner, sensitivity, allowed locations, permitted lifetime, prohibited destinations, and planned protection. Include:

- OpenAI/Codex authenticated session.
- Telegram bot/transport authorization.
- Provider OAuth/API credentials.
- Windows user session and local IPC secret.
- Phone device private key and registered public key.
- Pairing codes, session identifiers/challenges, and TURN credentials.
- Codex task identity and recent-task metadata.
- Phone microphone audio and Codex output audio.
- Operational logs and diagnostic bundles.
- Installation/update artifacts and signing keys.

### 4. Threat actors and capabilities

Cover at least:

- Random internet user who discovers the URL.
- Attacker replaying a pairing/session message.
- Stolen or malicious paired phone.
- Compromised Telegram account or unauthorized Telegram participant.
- Compromised provider account/control plane.
- Malicious or compromised user-level local process.
- Network observer or hostile NAT/Wi-Fi.
- Compromised separate-host Hermes node in the deferred topology.
- Malicious dependency or update artifact.
- Accidental operator error, stale session, or wrong-task selection.

Do not overstate protection against a fully compromised Windows user session; record this as a trust assumption/residual risk.

### 5. Trust boundaries and planned authentication matrix

For each boundary, state initiator, receiver, data, planned authentication, confidentiality/integrity mechanism, authorization decision owner, replay control, and failure behavior. Include:

- Telegram owner to Hermes.
- Hermes to same-host companion.
- Deferred separate-host Hermes to companion.
- Companion/Codex adapter to Codex desktop.
- Companion to provider control plane.
- Phone browser to page/signaling endpoint.
- Phone browser to active companion session.
- WebRTC direct path and TURN-relayed path.
- Companion/update installer to update source.

Planned controls that must be named:

- Telegram authorization inherited from a correctly configured Hermes owner policy; the plugin does not duplicate or extract Telegram credentials.
- Same-host named pipe or loopback IPC protected by per-user ACLs plus an installation-specific secret, to be chosen/tested later.
- Device-key pairing, short-lived signed challenge, host/session/device binding, expiration, rate limiting, and revocation.
- TLS for page/signaling; WebRTC DTLS-SRTP for media; short-lived TURN credentials.
- Provider secrets stored through Windows Credential Manager or equivalent OS-protected storage.
- Codex credentials never read by the integration; control occurs inside the current interactive user session.
- Signed/checksummed update artifacts and a future release-key policy; explicitly not implemented yet.

### 6. Abuse cases, controls, and residual risks

Create a traceable table with ID, scenario, affected assets, preventive controls, detective controls, recovery/revocation, residual risk, and owning later checkpoint. Include URL leakage, pairing brute force, replay, stolen phone, compromised provider, forged Hermes request, malicious local process, task confusion, system-audio leakage, PC-mic fallback, abandoned metered session, TURN credential theft, update tampering, logs leaking content, and Windows locking mid-call.

### 7. Frozen privacy invariants

State these as normative **MUST/MUST NOT** rules:

- No bridge recording or added transcript.
- No audio, prompt, task content, Codex response, or transcript in logs/diagnostics.
- No OpenAI, Telegram, provider, Windows, or device private credential in prompts or logs.
- URL knowledge alone is insufficient.
- Phone page cannot activate Codex.
- No silent physical-PC-microphone fallback.
- No silent system-wide audio capture fallback.
- End Session does not cancel/delete the task.
- No project-operated mandatory shared service.
- No billable provider resource without explicit preview and approval.

### 8. Logging and diagnostics policy

Define an allowlist of operational metadata and a denylist. Allowed examples: component/schema version, coarse timestamps/durations, lifecycle state names, sanitized error categories, browser family/capability result, ICE candidate class without addresses, cleanup result, and non-identifying device label. Deny exact paths, IPs, usernames, task titles unless deliberately redacted, raw command output, SDP/ICE payloads, tokens, and content.

### 9. Assumptions, limitations, and deferred validation

Map unresolved controls to checkpoints CP-004, CP-010–016, CP-020–026, CP-030–035, CP-040–046, CP-150, CP-153, and CP-154. Explicitly state that a compromised unlocked Windows session is outside the bridge's ability to fully defend.

### 10. Review checklist

Include a checklist mapping every CP-003 pass criterion to a document section.

## Artifact 2 — `data-flow-v0.md`

Use this structure.

### 1. Purpose and notation

Define data classifications: credential/secret, sensitive content, sensitive metadata, operational metadata, public artifact. Define arrow labels for control, media, signaling, and provider management.

### 2. Component/trust-boundary diagram

Include a readable Mermaid flowchart showing:

- Telegram user/client and Telegram service.
- Hermes agent/gateway.
- Same-host Windows trust boundary with companion, Codex adapter, audio engine, and Codex desktop.
- Phone browser/device trust boundary.
- User-owned Cloudflare/provider trust boundary with page/signaling, STUN, and TURN.
- OpenAI service boundary only as reached by Codex desktop; the bridge does not hold OpenAI credentials.
- Update/release boundary.
- Deferred separate-host Hermes route clearly dashed/labeled future.

If Mermaid syntax becomes too dense, use two diagrams: control plane and media plane.

### 3. Data-flow catalog

Assign stable IDs such as `DF-01`. For each flow, record source, destination, trigger, data, classification, transport, planned authentication, permitted persistence, forbidden logging, and owning checkpoint. Include setup/pairing, normal new/resume, task enumeration metadata, Voice ready notification, phone join, WebRTC negotiation, direct media, TURN media, reconnect, End Session, provider management, diagnostics, device revocation, and updates.

### 4. Storage and retention catalog

For each component, state what may be persisted and deletion/revocation behavior. The phone may retain its device private key and trust metadata; the host may retain device public key/trust record and protected provider/IPC credentials; the bridge may retain sanitized operational logs under a future bounded policy. Audio/content/session/TURN credentials are ephemeral or not persisted.

### 5. Lifecycle data minimization

Walk through one-time setup, start, active call, reconnect grace, end, revoke, uninstall, and crash recovery. State what is created, retained, invalidated, or deleted at each step.

### 6. Owner authorization assumptions

Document the inherited Hermes/Telegram authorization assumption. The companion accepts only narrow authenticated operations; it does not treat arbitrary Telegram text or possession of a web link as authority. If Hermes authorization cannot identify the owner reliably, session activation must be disabled rather than broadened.

### 7. Contradiction check

Explicitly compare the data-flow result with the canonical plan's packaging, lifecycle, user-owned networking, pairing, privacy, and separate-host sections. List `No contradiction found` only when each named point was checked.

## Artifact 3 — ADR 0001

Title: **User-owned infrastructure with no mandatory project-operated shared service**.

Required sections:

- Status: Accepted as architecture baseline; provider mechanism still subject to Phase Zero.
- Context.
- Decision.
- Decision drivers.
- Consequences, including user setup/account responsibility and the project's reduced central data/cost burden.
- Alternatives considered:
  - Project-operated shared signaling/relay service.
  - Mandatory custom domain/named tunnel.
  - Local-LAN-only product.
  - User-owned generic VPS as the only path.
- Security/privacy consequences.
- Operational/cost consequences.
- Revisit triggers.
- Related checkpoints.

The ADR may name Cloudflare as the intended first candidate and a provider-assigned hostname as acceptable, but it must not freeze an untested exact Workers/Tunnel/TURN architecture. Quick Tunnels must be labeled development-only rather than the production decision.

## Worker report

`work/cp-003-worker-report.md` must include:

- Files created.
- Source documents read.
- Boundary/authentication coverage summary.
- Privacy-invariant coverage summary.
- Contradictions found and how they were resolved.
- Remaining controls deferred to later checkpoints.
- Sensitive-data/publication self-check.
- Verification performed.
- Explicit statement that no system/application/provider state changed.
- Explicit statement that CP-003 completion is left to Codex.

## Verification required before handoff

Perform documentation-only checks:

1. Confirm all four files exist and are non-empty.
2. Confirm only the three public documentation files are visible to Git; `work/cp-003-worker-report.md` remains ignored/private.
3. Confirm every component and boundary named in CP-003 appears in the threat model/data flow.
4. Confirm each network/process boundary has an authentication method or is explicitly deferred/out of scope.
5. Confirm named controls exist for media confidentiality, device revocation, provider-secret storage, local IPC, and software-update trust.
6. Confirm all frozen privacy invariants are present using normative language.
7. Confirm all relative Markdown links resolve.
8. Validate Mermaid blocks for balanced fences and obvious syntax errors; do not install tooling solely for this.
9. Scan public files for personal paths, IP/MAC addresses, phone numbers, tokens, credential-like strings, prompts, tasks, transcripts, and audio references that disclose content.
10. Run `git diff --check` and review the exact diff, but do not commit.

## Acceptance criteria

Codex may accept CP-003 only if:

- Every process and network boundary has a named planned authentication method or is explicitly deferred/out of scope.
- Every required asset, threat actor, abuse case, and privacy invariant is covered.
- Media confidentiality, device revocation, provider secret storage, local IPC, and update trust each have a named control and later validation owner.
- The data flow distinguishes control, signaling, direct media, relay media, persistence, and deletion.
- Owner authorization assumptions are explicit and fail closed.
- ADR 0001 preserves user ownership and no mandatory shared service without prematurely freezing an untested provider mechanism.
- Documents make no false implementation/security claims and contradict none of the canonical product decisions.
- Public files contain no private CP-002 evidence or sensitive values.

## Worker handoff format

Report:

1. Files created.
2. Boundaries and assets covered.
3. Authentication/control gaps explicitly deferred.
4. Verification results.
5. Any contradiction or blocker.

Do not claim CP-003 is complete, commit, push, or begin CP-040/CP-044. Codex will independently review, request rework if necessary, then update status and publish the accepted checkpoint commit.
