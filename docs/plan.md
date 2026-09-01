# Hermes Codex Voice Remote — Detailed Product and Build Plan

Status: architecture plan, prior to implementation  
Initial supported platform: Windows  
Working name: **Hermes Codex Voice Remote**

> [!IMPORTANT] Mandatory implementation workflow
> **Codex is the planner, technical reviewer, and checkpoint authority. Grok 4.6 in Cursor is the implementation/worker agent.** Before any checkpoint is implemented, Codex writes a checkpoint-specific implementation plan with scope, files, tests, evidence, and acceptance criteria. Grok 4.6 implements that plan without expanding its scope. Codex then independently inspects the changes, runs or verifies the required tests, and compares the evidence with the checkpoint criteria. If the work passes, Codex updates the checkpoint map and Obsidian project note, commits and pushes the accepted public-safe checkpoint outcome to `main`, and plans the next checkpoint. Private machine evidence, credentials, audio, transcripts, prompts, task content, and personal paths are never published merely to satisfy this rule. If the work fails or is incomplete, Codex writes a precise rework request for Grok and reviews the revision again; failed or unaccepted work is not represented as a completed-checkpoint commit. A worker report alone never completes a checkpoint, and a different implementation agent is not substituted without the user's approval.

## 1. Product definition

Hermes Codex Voice Remote is a free, open-source Hermes package that lets a person use the **real Codex Voice experience running on their own Windows PC** from a lightweight browser page on a phone.

The intended interaction is:

1. The Windows PC is powered on, awake, unlocked, signed into the user's Windows profile, and already signed into Codex.
2. Hermes is running either on that PC or on another user-controlled host paired with it.
3. From Telegram, the user asks Hermes to start a new Codex Voice task or resume an existing task.
4. Hermes invokes deterministic companion tools that launch Codex, select the correct task, and start Voice.
5. Only after Codex Voice is verified as ready, Hermes sends the user the current phone-page link. The user does not need to remember, bookmark, or choose its hostname.
6. The phone browser sends its microphone audio to the Windows companion. The companion presents that audio to Codex as microphone input.
7. The companion captures only Codex's audio output and sends it back to the phone.
8. Ending the remote Voice session stops the media bridge and Codex Voice mode, but does not close, cancel, or delete the underlying Codex task. Codex work may continue normally.

This is not a new voice model, an imitation of Codex Voice, a remote-desktop product, or a hosted multi-user service. It is a private audio-and-control bridge into the user's own licensed Codex desktop session.

## 2. Final product contract

### 2.1 Requirements already decided

- The project is free and open-source.
- It is distributed as one product: one repository, one guided installation, and one Hermes capability.
- Internally it remains modular: Hermes plugin, Windows companion, Codex adapter, audio engine, embedded phone page, provider adapters, installer, and diagnostics.
- Windows is the first supported platform. macOS is not promised until somebody can build and test it properly.
- The PC running Codex must be powered on, awake, unlocked, and signed into its Windows user profile.
- Codex must be installed and the user must sign into Codex directly. The package never requests, sees, or stores OpenAI credentials.
- The user's plan or workspace must have access to Codex Voice, and Voice must work locally before remote setup proceeds.
- Hermes is the activation mechanism. The phone page cannot silently start Codex or turn on the bridge by itself.
- The phone client is a minimal HTTPS browser page intended for broad phone compatibility, including supported iPhone and Android browsers. No ChatGPT or Codex mobile app is required.
- Browser support is capability-based, not tied to one phone model. The page uses feature detection for secure-context microphone access, WebRTC/Opus, WebSocket, and the cryptographic/storage features required for device trust, and it fails clearly on unsupported browsers.
- The page source and assets are bundled with the product. A provider adapter may serve them from the Windows companion or automatically provision the same minimal page/signaling component in the user's own provider account. Users do not create, edit, or manually deploy a separate frontend project.
- Every user supplies and controls their own internet meeting point: tunnel, signaling endpoint, and relay service or account.
- The project operates no mandatory shared control plane, signaling service, or media relay.
- A custom domain is not required. A provider-assigned HTTPS address is acceptable, whether stable or generated for the active route, because Hermes supplies the current link after the session is ready.
- Audio should be direct peer-to-peer when possible, with an encrypted TURN relay fallback supplied by the user when direct connectivity fails.
- ICE path selection is automatic. A Home/Away switch is not part of the normal interface. Advanced diagnostics may offer direct-only or relay-only testing.
- Only one Codex Voice conversation may be remotely active on a host at a time.
- Hermes infers “new” or “resume” when the request is clear and asks only when it is ambiguous.
- When resuming, Hermes may offer the ten most recent supported Codex tasks, including enough context to distinguish duplicate titles.
- Hermes reports the page as ready only after it has verified the selected task and verified that Codex Voice is active.
- The phone microphone is the only microphone sent to Codex during a remote session. The companion must never silently fall back to the PC's physical microphone.
- The bridge records no audio and creates no additional transcripts.
- The page URL is not treated as a secret, whether it is stable or regenerated. Device pairing and per-session authorization protect access.
- A trusted phone should not require a fresh code for every short break. Trust duration is configurable; the recommended default is 30 days.
- A short connection loss or a closed browser page receives a reconnect grace period. A five-minute break must not force re-pairing.
- Explicitly ending the remote Voice session stops the audio bridge and Voice mode but preserves the Codex task and any ongoing work.

### 2.2 Explicit non-goals for the first release

- Waking a sleeping or powered-off PC.
- Unlocking Windows, storing a Windows password, or bypassing the lock screen.
- Supporting unattended execution on the Windows secure desktop.
- Providing a general remote desktop or screen stream.
- Showing the Codex window on the phone.
- Replacing Codex authentication or subscription requirements.
- Reimplementing Codex Voice with an OpenAI API voice model.
- Hosting a central service for all users.
- Saving recordings, transcripts, prompts, task content, or model responses in the bridge.
- Supporting multiple simultaneous remote Voice sessions on one PC.
- Supporting every tunnel or cloud provider in version one.
- Promising native-call-style background or screen-lock continuity on every phone browser; this must be measured per supported browser family and version.

## 3. User experience

### 3.1 One-time guided setup

The package presents a single setup wizard, even though several components are installed behind it.

1. **System check**
   - Confirm a supported Windows version.
   - Confirm the PC is running an interactive, unlocked user session.
   - Check required permissions and whether installation of an audio component will require administrator approval or a restart.

2. **Codex check**
   - Detect whether the Codex desktop experience is installed.
   - If it is missing, guide the user to the official installer.
   - Open Codex and ask the user to sign in directly if needed.
   - Verify sign-in without reading or exporting credentials.
   - Ask the user to complete one local Voice test.
   - Verify that a Voice session can be started and stopped locally.

3. **Hermes topology check**
   - Ask whether Hermes is running on this Windows PC or on another user-controlled host.
   - Same-host mode uses local authenticated IPC and is the first implementation target.
   - Separate-host mode pairs Hermes with the Windows companion through an authenticated node connection and is implemented after the same-host path is stable.

4. **Audio check**
   - Detect supported audio devices and virtual audio components.
   - Install or guide installation of the selected virtual microphone solution.
   - Verify that the companion can inject a test signal into the virtual microphone.
   - Verify that it can capture Codex application audio without capturing other applications or system sounds.
   - Restore all audio settings after the test, including after failure.

5. **User-owned connection setup**
   - Explain that the user must supply their own remote-access provider or server.
   - Offer only provider adapters that the project has actually tested.
   - The first reference adapter should be selected by feasibility testing. For Cloudflare, test a random `trycloudflare.com` Quick Tunnel only as a Phase Zero/development route, and test an automatically provisioned user-owned `workers.dev` page/signaling endpoint as the leading stable personal route. Direct WebRTC and TURN remain separately verified concerns.
   - Authenticate to the provider through its supported flow. Store provider secrets in Windows Credential Manager, never in the Hermes prompt or skill text.
   - Create or validate a provider-assigned HTTPS hostname. A custom domain is optional, not a prerequisite.
   - Validate HTTPS, WebSocket signaling, STUN, TURN credentials, and expiration behavior.
   - Do not perform deployments or create billable resources without showing the operation and receiving the user's approval.

6. **Phone pairing**
   - Start the personal page temporarily and show both a QR code and a tappable URL.
   - The phone browser generates its own device key pair.
   - The user enters a short, one-time pairing code delivered by Hermes or displayed locally during setup.
   - The host associates the device's public key with a user-selected trust lifetime.
   - The private key remains on the phone, preferably non-exportable through WebCrypto.
   - The setup shows the initial page link. Bookmarking or Add to Home Screen is optional because Hermes sends the current link for every started session.

7. **End-to-end test**
   - Hermes starts a disposable Codex Voice test task.
   - The phone joins using the paired device.
   - The wizard tests microphone input, Codex output, mute, output mute, reconnect, and End Session.
   - The wizard confirms that ending Voice left the Codex task intact.
   - Setup completes only when all mandatory checks pass or the user explicitly accepts a documented degraded mode.

### 3.2 Normal session: new task

1. The user messages Hermes with a clear request such as “Start a new Codex Voice task.”
2. The skill checks companion availability, Codex installation state, provider health, device trust, and whether another Voice session is active.
3. The companion launches Codex if necessary.
4. The companion creates a new task in the appropriate project or context. If context is missing and materially changes the result, Hermes asks the user.
5. The companion verifies the created task rather than assuming the last click succeeded.
6. The companion starts Codex Voice and waits for a positive ready signal.
7. The companion activates the temporary remote media session and its signaling route.
8. Hermes tells the user the session is ready and sends the current page link. A fresh pairing code is not required while device trust remains valid.
9. The browser authenticates with its device key, receives an ephemeral session authorization, and establishes WebRTC.
10. The call screen becomes active only after both microphone and output paths are ready.

### 3.3 Normal session: resume task

1. If the user names a task clearly, Hermes asks the companion to resolve it deterministically.
2. If the request is ambiguous, Hermes offers up to ten recent supported tasks.
3. Each option includes title plus project, recency, or another safe discriminator. Duplicate titles must not be selected by title alone.
4. The user selects a task.
5. The companion opens the task and verifies the selected identity before starting Voice.
6. The remainder of the flow matches a new session.

### 3.4 During a call

The phone interface remains deliberately small:

- Connection state: connecting, ready, reconnecting, ended, or actionable error.
- Microphone mute.
- Codex/output mute. This affects phone playback only; it does not pause Codex.
- End Session.
- A minimal indication of which Codex task is attached.
- Optional input-device selection on desktop browsers. On phones, the browser and operating system control the active microphone and speaker route.

The page does not need a software volume slider because normal volume is controlled by the phone. It should not expose unrelated Codex controls, recent task lists, provider settings, or setup controls during a call.

### 3.5 Disconnect, reconnect, and ending

- Closing the page, switching networks, or a temporary transport loss does not immediately end the session.
- The companion enters a reconnect state. The recommended default grace period is ten minutes, comfortably covering a five-minute break.
- A trusted device can reopen the current link supplied by Hermes and rejoin without a new pairing code.
- No audio is injected while the phone is disconnected, and the PC microphone is never substituted.
- If the user taps **End Session**, the companion stops the WebRTC session, stops microphone injection, exits Codex Voice mode when safe, releases audio devices, and deactivates the temporary route.
- Ending the remote session must not cancel, close, archive, or delete the Codex task.
- An explicit Hermes command can also end the remote Voice session.
- Cancelling an active Codex task is a separate explicit command and is never implied by ending the call.

## 4. Packaging and repository structure

Externally, the project is one installable Hermes extension package. Internally, it should have clean boundaries:

```text
hermes-codex-voice-remote/
  plugin/                 Hermes manifest, skill, and tool definitions
  companion/              Windows per-user companion and state machine
  codex-adapters/          Codex launch, task, and Voice-control adapters
  audio/                  Capture, virtual microphone, codec, and device logic
  web/                    Embedded phone page and pairing UI
  providers/              Tunnel, signaling, STUN, and TURN adapters
  installer/              Guided setup, upgrade, repair, and uninstall
  protocol/               Versioned IPC and remote-node schemas
  tests/                  Unit, integration, hardware, network, and UI tests
  docs/                   Setup, security, self-hosting, and troubleshooting
```

The repository may produce more than one executable, but the user experiences one installation and one capability.

## 5. Component architecture

### 5.1 Hermes plugin and bundled skill

The skill owns conversation behavior:

- Interpret start, resume, reconnect, end, status, and diagnostic requests.
- Infer new versus resume when clear.
- Ask concise questions only when ambiguity matters.
- Present recent tasks returned by the companion.
- Wait until the companion reports Voice ready before telling the user to join.
- Give actionable errors without inventing UI state.

The skill must not depend on a model visually clicking arbitrary screen coordinates. It invokes narrow, deterministic plugin tools such as:

- `voice_remote_status`
- `voice_remote_setup`
- `codex_recent_tasks`
- `codex_open_task`
- `codex_create_task`
- `codex_start_voice`
- `voice_remote_start`
- `voice_remote_stop`
- `voice_remote_devices`
- `voice_remote_revoke_device`
- `voice_remote_diagnose`

Exact names may change, but each tool must have a small, typed contract and idempotent behavior where possible.

### 5.2 Windows companion

The companion is the authoritative local controller. It should run as a per-user process started at Windows sign-in because Codex UI and audio belong to that interactive user session. A small privileged helper may be used only for installation or driver operations.

Responsibilities:

- Detect and launch Codex.
- Track supported Codex versions and adapter compatibility.
- List, create, open, and verify tasks.
- Start, verify, and stop Codex Voice.
- Own the session state machine.
- Capture Codex application audio.
- Receive and inject phone microphone audio.
- Serve the embedded phone page.
- Perform pairing and device authentication.
- Establish signaling and media connections through the user's provider.
- Expose authenticated local IPC to Hermes.
- Produce privacy-preserving diagnostics.
- Recover resources and restore settings after crashes.

Same-host IPC should use a Windows named pipe or loopback interface protected by per-user access controls and an installation-specific secret. It must not expose an unauthenticated local HTTP control API.

### 5.3 Codex adapter

The adapter must use the strongest available control method in this order:

1. Officially supported Codex control interface or documented deep link.
2. Verified Codex protocol handler or stable native automation interface.
3. Windows UI Automation using semantic roles, names, and state—not screen coordinates.
4. Stable keyboard commands with state verification.
5. Image or OCR assistance only as an optional last-resort adapter, never as the default reliability path.

The installed Windows package currently exposes a `codex://` protocol handler, which is a promising feasibility lead, not a contract. Phase Zero must discover what it can safely do and must not assume undocumented URLs will remain stable.

Every mutating action follows an act-and-verify pattern. For example, opening a task is successful only when the adapter confirms the intended task, not merely when a click was sent. If the installed Codex version is unknown or the verification signal is missing, the adapter fails closed with an actionable error.

### 5.4 Audio engine

The target audio graph is:

```text
Phone microphone
  -> browser WebRTC microphone track
  -> Windows companion decoder/jitter buffer
  -> virtual microphone endpoint
  -> Codex Voice input

Codex application output
  -> process-specific Windows audio capture
  -> Windows companion encoder
  -> browser WebRTC output track
  -> phone speaker/headphones
```

Requirements:

- Use Opus through WebRTC unless target-device testing proves another browser-native path is necessary.
- Capture only the Codex application process tree through Windows application loopback where supported.
- Never stream arbitrary system audio, notifications, music, or other applications.
- Never monitor the injected phone microphone through the PC speakers.
- Never substitute a physical PC microphone.
- Prefer selecting the virtual microphone inside Codex if Codex exposes a device selector.
- Avoid changing the global Windows default microphone.
- If a global-device switch is required as a fallback, make it explicit, transactional, opt-in, and crash-safe; always restore the previous device.
- Let the browser request echo cancellation, noise suppression, and automatic gain control, with diagnostics to disable them when troubleshooting.
- Handle Bluetooth and wired-headset route changes without silently switching to the PC microphone.

Windows does not provide a general user-mode virtual microphone for arbitrary applications. Phase Zero may use a separately installed virtual cable to prove the media path. Before release, the project must choose one legally and operationally supportable option:

- Depend on a documented third-party virtual audio device installed separately.
- Obtain redistribution permission for a suitable component.
- Build, sign, maintain, and install an open-source virtual audio driver.

Shipping a kernel audio driver is a major maintenance and code-signing commitment and must not be chosen casually.

### 5.5 Embedded phone page

The phone page is built into the product's release artifacts. It is not generated from scratch for each user. Depending on the qualified provider adapter, the identical bundled assets may be served from the companion through a tunnel or provisioned automatically into the user's own provider account. The user never creates or maintains a separate frontend project.

Requirements:

- Work as a normal HTTPS page with no App Store installation.
- Target a measured capability floor across representative mobile browsers, with iOS Safari/WebKit and Android Chromium as required test families and additional browsers added only when verified.
- Detect required capabilities at runtime and present a clear unsupported-browser result instead of guessing from the device name alone.
- Use native WebRTC rather than depending on modern application frameworks that inflate compatibility requirements.
- Keep JavaScript, CSS, fonts, and assets small.
- Request microphone permission only when joining a live session.
- Store device identity locally and securely.
- Show connection and permission failures in plain language.
- Remain usable with larger text and accessibility settings.
- Avoid mandatory PWA installation; “Add to Home Screen” is optional.

Mobile browsers may suspend microphone capture, audio playback, timers, or networking when backgrounded or when the screen locks. Phase Zero must measure this on representative supported browsers. Until a combination is proven, version one should document that the page must remain foregrounded and the screen awake during the call; reconnect after suspension remains required.

### 5.6 User-owned networking

The networking design separates three concerns:

1. **Page and signaling route** — HTTPS and WebSocket traffic that lets the phone load the embedded page and negotiate a session.
2. **Direct media connectivity** — WebRTC ICE and STUN attempt to connect phone and PC directly.
3. **Relay fallback** — TURN carries encrypted WebRTC packets when direct connectivity is blocked.

A tunnel alone does not automatically solve TURN. Each provider adapter must declare exactly which concerns it supplies.

The provider contract should support:

- Authenticate or validate user-owned provider credentials.
- Obtain or validate a provider-assigned HTTPS hostname and report whether it is stable across route restarts.
- Start and stop the personal route.
- Publish the companion's page and signaling endpoint.
- Supply STUN configuration.
- Mint short-lived TURN credentials or point to the user's own TURN server.
- Run connectivity and relay-only diagnostics.
- Report cost-affecting operations before they are enabled.
- Tear down or revoke resources during uninstall when the user requests it.

Version one should implement and test one reference provider well. Provider selection must be deterministic and documented, not improvised by the language model. Additional adapters can follow once their compatibility and security are tested.

For a fully self-hosted server path, the project may later provide a small reference deployment containing a reverse proxy, signaling endpoint, and Coturn configuration. That deployment remains in the user's infrastructure.

### 5.7 Same-host and separate-host Hermes

**Same-host mode** is implemented first:

- Hermes plugin and Windows companion communicate locally.
- Codex, Hermes, and the audio bridge are on the same unlocked PC.
- This removes one network and authentication boundary during initial development.

**Separate-host mode** is a later required capability:

- Hermes runs on a user-controlled server or other device.
- The Windows companion remains installed on the unlocked Codex PC.
- The two pair using device keys and an authenticated, encrypted control channel through the user's meeting point.
- Only narrow companion operations are exposed. The Hermes server does not receive Windows or OpenAI credentials.
- The Windows companion remains the authority for local state and can reject stale, unauthorized, or unsafe requests.

## 6. Authentication and security model

### 6.1 Principles

- The permanent URL is an address, not an authentication secret.
- Possession of a Telegram chat link alone must not authorize microphone access or control.
- Valid device trust allows a device to join a session only after Hermes has activated one; it does not grant the phone permission to start Codex by itself.
- Provider, OpenAI, Windows, and Telegram credentials remain in their native trust boundaries.
- Audio content is never intentionally persisted by the bridge.

### 6.2 Device pairing

1. The phone creates a device key pair.
2. The host generates a one-time, short-lived pairing code.
3. Pairing attempts are rate-limited and locked out after repeated failures.
4. Successful pairing records the public key, a friendly device name, creation time, and trust expiration.
5. Default device trust is 30 days; setup may offer one day, one week, one month, or a custom policy.
6. New devices, expired devices, cleared browser storage, and revoked devices require pairing again.
7. The user can list and revoke paired devices through Hermes and the local setup application.

### 6.3 Session authorization

- Each remote Voice session gets a fresh ephemeral session identifier and challenge.
- The paired device signs the challenge.
- Authorization is bound to the host, active session, device, and short expiration.
- TURN credentials are short-lived and session-scoped.
- Reconnection during the grace period uses a fresh challenge but not a new pairing code.
- Session credentials are invalidated when End Session completes.

### 6.4 Secret storage and privacy

- Provider credentials use Windows Credential Manager or an equivalent OS-protected store.
- Local IPC secrets are generated at installation and protected with per-user ACLs.
- The browser private key stays on the phone.
- Logs contain operational metadata only: component version, state transitions, coarse timing, device class, and sanitized errors.
- Logs must not contain audio, transcripts, task prompts, task answers, OpenAI tokens, provider tokens, or Telegram tokens.
- Diagnostic bundles are locally previewed and scrubbed before a user shares them.
- Telemetry is off by default and requires explicit opt-in if it is added later.

## 7. Lifecycle and state model

The implementation must keep three lifecycles separate:

1. **Codex task lifecycle** — idle, running, waiting, completed, failed, or cancelled.
2. **Codex Voice lifecycle** — off, starting, ready, stopping, or failed.
3. **Remote media lifecycle** — inactive, awaiting phone, connecting, connected, reconnecting, ending, or failed.

Ending one lifecycle must not accidentally end another.

Recommended host session states:

| State | Meaning | Allowed next actions |
|---|---|---|
| Unconfigured | Setup incomplete | Run or repair setup |
| Ready | Companion healthy; no remote session | Start new or resumed session |
| Preparing task | Codex is launching or selecting a task | Wait or cancel preparation |
| Starting Voice | Correct task verified; Voice starting | Wait or fail safely |
| Awaiting phone | Voice ready; personal route active | Join, end, or timeout |
| Connected | Bidirectional audio active | Mute, reconnect, or end |
| Reconnecting | Phone temporarily disconnected | Rejoin within grace period or end |
| Ending | Media and Voice resources are being released | Wait for Ready |
| Error | A verified failure occurred | Diagnose, repair, or return to Ready |

Busy behavior:

- A second start request never destroys an existing session automatically.
- If the same paired device is reconnecting, Hermes directs it back to the active session.
- If a different request arrives while a session is active, Hermes reports that the host is busy and offers safe choices.
- If Codex is working without an active Voice session, starting Voice may attach to that task after explicit task resolution.
- If Codex Voice is already active but the companion cannot prove which task owns it, the companion refuses to attach rather than risk routing audio to the wrong task.

Timeout defaults to validate during testing:

- Task/Voice preparation timeout: fail and clean up rather than hang indefinitely.
- Awaiting phone timeout: approximately five minutes.
- Reconnect grace period: approximately ten minutes.
- No arbitrary maximum call duration beyond provider or Codex limits unless needed to prevent abandoned metered sessions.
- Any abandoned Voice session must eventually be detected and cleaned up without cancelling the underlying task.

## 8. Build phases

### Phase Zero — feasibility and evidence

Goal: prove the four hardest assumptions before committing to production architecture.

#### A. Codex-control spike

- Detect the installed Codex package and version.
- Investigate the existing `codex://` protocol handler safely.
- Determine whether supported APIs, deep links, UI Automation, or keyboard commands can:
  - Launch Codex from a closed state.
  - Create a task.
  - Enumerate recent supported tasks.
  - Open one exact task, including duplicate-title cases.
  - Start and stop Voice.
  - Detect Voice ready, error, and ended states.
  - Survive Codex relaunch and normal UI layout changes.
- Record which operations require the window to be foregrounded.
- Confirm behavior while the Windows PC is awake and unlocked.
- Establish an adapter boundary so the mechanism can change later.

Exit gate: at least 20 consecutive cold-start trials must open the correct task and reach a verified Voice-ready state with zero wrong-task attachments.

#### B. Windows-audio spike

- Install a test virtual audio endpoint without yet choosing a redistribution strategy.
- Send a prerecorded voice sample and live microphone sample into the virtual endpoint.
- Confirm Codex receives it as microphone input.
- Capture Codex application audio through process-specific WASAPI loopback.
- Prove that other application and system audio is excluded.
- Measure latency, jitter, CPU use, device-release behavior, and crash recovery.
- Test physical microphone unplugging and default-device changes.

Exit gate: clean full-duplex audio for a sustained test, no unintended system audio, no physical-microphone fallback, and settings restored after forced termination.

#### C. Broad phone-browser spike

- Define the required browser capability set and build a probe page.
- Test at least representative iOS Safari/WebKit and Android Chromium versions, with the user's older phone included when available as a compatibility data point rather than the sole target.
- Serve a minimal HTTPS WebRTC page.
- Test microphone permission, Opus, speaker/headset output, mute, output mute, reconnect, cellular data, Wi-Fi transitions, incoming phone interruptions, browser backgrounding, and screen locking.
- Measure added media latency and stability.
- Decide an evidence-based browser/OS support floor and runtime feature-detection rules.

Exit gate: 30-minute bidirectional calls on the required representative browser families with understandable audio, successful controls, and documented background/screen-lock behavior; unsupported devices fail clearly.

#### D. User-owned remote-network spike

- Choose the first reference provider candidate.
- Prove the page and signaling path through a provider-assigned HTTPS hostname; record whether the hostname is stable or changes when the route restarts.
- Test ICE direct connectivity across different networks.
- Force TURN-only mode and prove encrypted relay fallback.
- Switch between Wi-Fi and cellular.
- Measure connection time, relay cost behavior, and failure messages.
- Prove that stopping a session makes the media route unusable and invalidates session credentials.

Exit gate: successful connection on at least one direct path and one forced-relay path, with no manual deployment during normal session startup.

#### Phase Zero decision gates

- If Codex cannot be controlled reliably, do not build the installer around fragile screen-coordinate automation. Reassess official remote interfaces, version-pinned semantic automation, or the viability of the project.
- If microphone injection requires an unsupportable driver, choose a clearly documented external dependency or pause release rather than hiding the limitation.
- If a phone/browser combination cannot sustain WebRTC, exclude that combination through the published capability floor or redesign the affected browser function. A voice-note fallback may be a separate feature, but it is not presented as live Codex Voice.
- If user-owned remote networking cannot be made reproducible, narrow version one to a single documented provider rather than pretending to support arbitrary hosting.

### Phase One — foundation

- Create the monorepo and versioned component contracts.
- Define the companion state machine.
- Implement authenticated local IPC.
- Create a simulated Codex adapter and simulated audio endpoints for automated tests.
- Implement structured, content-free logging.
- Add build, lint, unit-test, and signed-artifact CI foundations.
- Document threat boundaries and data flow before external networking is enabled.

Exit gate: Hermes can drive a complete simulated session deterministically, including failures and cleanup.

### Phase Two — local same-host MVP

- Implement same-host Hermes plugin tools.
- Implement the first real Codex adapter.
- Implement local audio capture and injection using the Phase Zero test component.
- Embed the minimal phone page.
- Run over local HTTPS and LAN WebRTC first.
- Support new task, one selected existing task, Voice ready detection, mute, output mute, reconnect, and End Session.
- Keep the Codex task intact after ending Voice.

Exit gate: the target phone can hold a reliable LAN conversation with real Codex Voice, started entirely through Hermes after setup.

### Phase Three — robust task selection and automation

- Add recent-task enumeration and safe duplicate-title disambiguation.
- Add infer-when-clear and ask-when-ambiguous behavior to the skill.
- Add idempotent start/stop operations and busy-state handling.
- Add version detection, adapter capability reporting, and fail-closed behavior.
- Add crash restart, orphan-session detection, and transactional audio restoration.
- Test Codex updates against the adapter compatibility suite.

Exit gate: repeated new/resume flows never attach to the wrong task and recover cleanly from expected interruptions.

### Phase Four — user-owned remote connectivity

- Finalize the provider interface.
- Implement one fully tested reference provider.
- Add stable hostname, HTTPS page delivery, WebSocket signaling, STUN, and TURN fallback.
- Add device pairing, public-key trust, trust expiration, revocation, and ephemeral session authorization.
- Add relay-only diagnostics and network-transition recovery.
- Keep the normal interface on automatic ICE path selection.

Exit gate: the user can start through Telegram and converse from cellular data without deploying a web page or manually starting infrastructure.

### Phase Five — setup wizard and packaging

- Build system, Codex, Voice, Hermes-topology, audio, provider, and phone-pairing checks.
- Package the Hermes plugin, companion, embedded page, and supported dependencies as one guided install.
- Add administrator elevation only where necessary.
- Add repair, upgrade, rollback, and uninstall flows.
- Ensure uninstall can revoke device trust and remove provider resources when requested without deleting unrelated user resources.
- Create a local health screen and Hermes diagnostic flow.

Exit gate: a clean supported Windows machine can complete setup using the documentation without manually editing source or deploying a frontend.

### Phase Six — separate-host Hermes

- Implement authenticated companion-node pairing.
- Route narrow control operations from the remote Hermes host to the Windows companion.
- Add replay protection, host identity verification, revocation, and offline behavior.
- Keep provider and OpenAI credentials on the Windows PC or in their native provider boundary.
- Test Hermes-host restart, Windows-companion restart, and temporary loss of the control channel.

Exit gate: Hermes on a user-controlled server can safely start and manage Voice on the unlocked Windows Codex PC with the same user experience.

### Phase Seven — hardening and beta

- Complete the security review and threat tests.
- Run long-call, repeated-call, crash, update, network-roaming, and device-change tests.
- Test all supported Windows, Codex, browser, and provider versions.
- Test expired trust, stolen link, revoked device, brute-force pairing, stale session, and replay attempts.
- Verify that no audio or task content appears in logs, caches, crash reports, or diagnostics.
- Create troubleshooting decision trees and a privacy/security document.
- Run a small beta with users who own their meeting-point infrastructure.
- Use beta evidence to freeze the supported matrix.

Exit gate: release criteria below are satisfied without undocumented manual recovery steps.

### Phase Eight — open-source release

- Choose licenses compatible with every bundled component.
- Publish architecture, threat model, provider contract, contribution guide, and support boundaries.
- Publish checksums or signatures for release artifacts.
- Clearly label Windows as supported and other platforms as unsupported/experimental.
- Document provider costs and resource ownership without claiming that third-party services are free forever.
- Establish a compatibility policy for Codex UI changes.
- Publish the first stable release only after the reference setup works end to end.

## 9. Test strategy

### 9.1 Automated tests

- State-machine transition and idempotency tests.
- Protocol compatibility and schema tests.
- Device-pairing, challenge, expiration, revocation, and replay tests.
- Provider adapter contract tests using local fakes.
- Audio-buffer, jitter, resampling, mute, and cleanup tests.
- Embedded-page compatibility tests for supported browser syntax and APIs.
- Installer upgrade, repair, and uninstall tests in clean Windows virtual machines where possible.
- Codex-adapter tests against recorded semantic UI fixtures, with real-app smoke tests kept separate.

### 9.2 Real-system matrix

- Codex closed, minimized, backgrounded, already open, and recovering from a crash.
- New task, exact resume, duplicate titles, no recent tasks, and unsupported task types.
- Voice already active, task active without Voice, and abandoned Voice session.
- PC audio-device insertion/removal and Bluetooth changes.
- Phone on home Wi-Fi, external Wi-Fi, cellular, restrictive NAT, and forced TURN.
- Phone browser foreground, background, screen lock, permission denied, microphone revoked, and incoming call interruption.
- Hermes same-host and separate-host configurations.
- Provider credential expiration, quota failure, tunnel failure, TURN failure, and DNS/TLS failure.
- Codex update that changes automation selectors.
- PC lock or sleep during a session: fail clearly and never attempt to unlock or wake it.

### 9.3 Quality targets to validate

- Zero wrong-task Voice attachments in the release qualification run.
- No capture of non-Codex system audio.
- No physical-PC-microphone fallback.
- No audio, transcripts, prompts, or model responses in bridge logs.
- Session startup should normally reach a joinable page shortly after Codex reports Voice ready; exact latency target is set from Phase Zero measurements.
- Added bridge latency should remain low enough for natural interruption and turn-taking; establish a numeric p95 target after measuring representative supported phones and networks.
- Reconnect should complete within a few seconds on a healthy network and never require re-pairing during the valid trust period.
- A forced crash must release or recover audio devices and restore any modified settings.

## 10. Reliability and failure behavior

- Every start operation has a timeout and compensating cleanup.
- The system does not send “ready” based only on process launch.
- If Codex cannot be found, the skill tells the user whether installation, sign-in, Voice eligibility, or adapter compatibility failed.
- If the correct task cannot be verified, Voice is not started.
- If the virtual microphone is unavailable, the PC microphone is not substituted.
- If application audio capture fails, system-wide loopback is not used silently.
- If direct WebRTC fails, TURN is attempted automatically when configured.
- If TURN is unavailable, the error identifies the user's provider component that needs repair.
- If the phone disappears, the companion holds only the reconnect grace period, then releases metered Voice and media resources while preserving the task.
- On companion restart, orphaned routes and audio state are reconciled before accepting a new session.
- A Codex update that invalidates the adapter disables unsafe actions until compatibility is restored.

## 11. Principal risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| No stable Codex Voice control interface | UI automation may break after updates | Investigate deep links/APIs first; semantic UIA fallback; version detection; fail closed; adapter compatibility tests |
| Virtual microphone requirement | May require a signed driver, admin rights, licensing, and reboot | Prove with external test component; make an explicit dependency/driver decision before release; never hide installation impact |
| Mobile-browser fragmentation | WebRTC, codecs, permissions, background audio, or modern JS may differ by browser and OS | Keep the page framework-light; use runtime feature detection; test representative iOS and Android combinations; publish an evidence-based compatibility matrix |
| Browser suspension when phone locks | A web page may not behave like a native call app | Require foreground/screen awake until verified; provide reconnect rather than promising unsupported background behavior |
| Tunnel mistaken for TURN | Page may load while media fails on restrictive networks | Separate provider capabilities; require forced-relay test before setup passes |
| Arbitrary-provider ambition | Many combinations become untestable | Ship one reference adapter first; document a provider contract; add adapters only with tests |
| Model-driven computer use | Screen-reading actions may be slow or nondeterministic | Put behavior in the skill but execution in narrow deterministic companion tools |
| Separate Hermes host | Adds another authentication and availability boundary | Same-host first; explicit node pairing; narrow authenticated protocol later |
| Voice sessions left running | May consume limits or cost and hold devices | Preparation, join, reconnect, and orphan timeouts; explicit session state; cleanup without cancelling task |
| Central-service creep | Conflicts with personal, user-owned design | No mandatory project-operated service; provider resources remain in each user's account |
| Secret leakage | Provider or account compromise | Native credential storage; no secrets in prompts/logs; device keys; ephemeral credentials; diagnostics scrubbing |
| Wrong task selected | Could expose or modify unrelated work | Stable task identity, disambiguation, act-and-verify, and zero-tolerance release testing |

## 12. Release definition of done

The Windows-first release is complete only when a new user can:

1. Install one package through a guided flow.
2. Confirm or install Codex and sign in directly.
3. Prove local Codex Voice works.
4. Connect one supported user-owned provider without manually deploying the phone page.
5. Pair an eligible phone through a QR code and one-time code.
6. Ask Hermes to create or resume the correct Codex task.
7. Receive a ready notification only after real Codex Voice is active.
8. Open the link Hermes supplies and hold a two-way conversation from outside the home network.
9. Reconnect after a five-minute break without receiving another pairing code.
10. End the remote Voice session while leaving the Codex task intact.
11. Review and revoke paired devices.
12. Diagnose common failures without exposing private task content.
13. Upgrade, repair, and uninstall without leaving audio settings, credentials, or project-owned resources in an unsafe state.

Release also requires:

- The reference provider path passes direct and forced-relay tests.
- Codex automation passes repeated cold-start and resume tests with no wrong-task attachment.
- The selected virtual microphone solution has a viable license, installation, update, and support story.
- Representative supported iPhone and Android browser combinations pass the documented compatibility tests, and unsupported combinations fail clearly.
- Security and privacy documentation matches implementation.
- No mandatory shared service operated by the project exists.

## 13. Decisions intentionally deferred to Phase Zero evidence

These are not missing product decisions; they are engineering choices that should not be guessed:

- The exact Codex automation mechanism and how much the `codex://` handler can safely do.
- The production virtual microphone component and its redistribution/signing model.
- The exact Cloudflare/provider-issued hostname mechanism used for production and whether it remains stable across route restarts; a custom domain is not required.
- The minimum supported mobile browser/OS capability matrix.
- Numeric latency and startup-time service targets.
- Which supported browser/OS combinations can keep a call alive while backgrounded or locked.
- Whether Codex offers a per-application microphone selector; global microphone switching remains a non-default fallback.

## 14. First implementation milestone

The first real milestone is deliberately narrow:

- Hermes, Codex, and the companion run on the same unlocked Windows PC.
- Codex is already installed and signed in.
- A test virtual microphone is installed manually.
- A representative phone browser opens a minimal HTTPS page on the local network, with the user's older phone tested when available.
- A Hermes command launches Codex, creates one new task, starts real Codex Voice, and reports ready.
- The phone can speak to Codex and hear Codex.
- Mute, output mute, reconnect, and End Session work.
- Ending leaves the Codex task intact.

This milestone intentionally excludes polished installation, recent-task selection, separate-host Hermes, provider automation, and public release. Its purpose is to prove the irreversible technical assumptions before the project invests in packaging.

## 15. Plan-to-checkpoint handoff

The subsequent checkpoint map should decompose this plan into ordered, verifiable checkpoints. Each checkpoint should contain:

- Objective.
- Inputs and prerequisites.
- Concrete implementation tasks.
- Evidence or test commands required to pass.
- Pass/fail exit criteria.
- Risks or decisions unlocked by the result.
- Dependencies on previous checkpoints.
- Files or artifacts produced.
- Rollback or fallback path if the checkpoint fails.

The checkpoint map should begin with Phase Zero evidence and should not schedule full installer or public-release work before the Codex-control, audio, phone-browser, and remote-network gates pass.
