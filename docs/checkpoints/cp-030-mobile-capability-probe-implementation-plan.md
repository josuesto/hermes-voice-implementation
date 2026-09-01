# CP-030 Implementation Plan — Mobile Capability Probe and Representative Browser Inventory

> **Mandatory workflow:** Codex is the planner, technical reviewer, and checkpoint authority. Grok 4.6 in Cursor is the implementation worker. Grok implements only this plan, does not mark completion, and does not commit or push. Physical-phone steps are user-operated; Grok must never fabricate device results. Codex independently reviews the probe and every submitted result before acceptance.

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-030**  
Depends on: **CP-004 — Complete**  
Scope: **Framework-free capability probe plus real-device inventory; no live PC audio bridge or production phone page**

## Objective

Define the minimum browser capabilities required by Hermes Voice Implementation, build a tiny privacy-preserving probe page, and collect real evidence from representative iOS Safari/WebKit and Android Chromium phones. The result must support a capability-based compatibility target rather than promising all phones or optimizing only for the creator's older iPhone.

CP-030 does not prove a 30-minute call, WebRTC interoperability with the companion, background behavior, or final UI. CP-031 through CP-035 own those proofs.

## Completion reality

The worker can build and locally self-test the probe, but CP-030 cannot be Complete from desktop simulation alone. At least one physical iPhone/iOS Safari-WebKit combination and one physical Android/Chromium combination must run the probe. The creator's older phone should be included when available, but it is not the sole target.

If representative physical devices or a safe temporary HTTPS origin are unavailable, complete the build/static-test portion, mark the checkpoint In progress/Blocked, and return an exact user test request. Do not invent versions or treat desktop emulation as physical-device evidence.

## Working locations

The execution workspace is maintainer-local, private, and ignored by Git. Its absolute path is intentionally unpublished. All `work/` paths below are relative to that private workspace and are not public-repository artifacts.

Create or edit only:

```text
work/feasibility/phone/cp-030/
  README.md
  probe/
    index.html
    probe.js
    probe.css
  schema/
    mobile-capability-result.schema.json
  scripts/
    Test-MobileCapabilityProbe.ps1
    Import-MobileCapabilityResult.ps1
  reports/
    required-capabilities.md
    representative-device-plan.md
    capability-matrix.md
    results/                         # sanitized imported physical-device results
  cp-030-worker-report.md
```

The shared harness may add sanitized CP-030 records under `work/feasibility/phone/results/`.

Public read-only sources:

- [`docs/plan.md`](../plan.md), [`docs/checkpoint-map.md`](../checkpoint-map.md), and [this CP-030 implementation plan](cp-030-mobile-capability-probe-implementation-plan.md);
- [`docs/security/threat-model-v0.md`](../security/threat-model-v0.md) and [`docs/security/data-flow-v0.md`](../security/data-flow-v0.md);
- authoritative browser/platform documentation only when required to interpret an API, with URLs and access dates recorded in `required-capabilities.md`.

Private read-only sources, not included in Git:

- CP-002 capability-based phone decision and supporting inventory.
- CP-004 harness, schema, and privacy scripts.

Do not edit the public repository during worker implementation.

## Mandatory privacy and safety boundaries

- The probe must not transmit results, audio, device identifiers, or telemetry to any backend.
- The probe must not record, encode, save, upload, or play back microphone audio.
- Microphone permission may be requested only after an explicit user tap and only during the physical-device step.
- On permission success, inspect safe track/settings capability categories, stop every track immediately, release the stream, and retain no samples.
- Do not use `MediaRecorder`.
- Do not collect full user-agent strings, advertising identifiers, device names, local IPs, ICE candidates, SDP, hostnames, phone numbers, account data, storage contents, or network addresses.
- Do not enumerate media-device labels or persist device IDs. Record only safe counts and permission state after permission, if needed.
- Do not enumerate local files, contacts, Bluetooth devices, or unrelated browser storage.
- Do not install a native app, configuration profile, root certificate, PWA, VPN, or browser extension.
- “Add to Home Screen” remains optional and is not tested as a prerequisite.
- Do not deploy to Cloudflare, GitHub Pages, Vercel, or another provider without a separate explicit approval describing the temporary resource, public URL, cost, and cleanup. CP-030 itself does not authorize provider login or resource creation.
- A Cloudflare Quick Tunnel may be considered only as a development-only temporary HTTPS transport after explicit approval and availability checks; it is never a production/provider qualification result.
- Do not weaken TLS or tell the user to bypass a certificate warning.
- Do not claim background/screen-lock support; CP-034 owns that evidence.
- Do not substitute third-party WebRTC test pages for the project probe's required result schema.

## Required capability model

Define every capability as `required`, `optional`, `degraded`, or `not-used`, with a rationale and owning later checkpoint.

At minimum probe:

### Secure page and media input

- `window.isSecureContext`;
- `navigator.mediaDevices` and `getUserMedia` presence;
- microphone permission flow after a user gesture;
- permission denied/dismissed/unavailable categories;
- immediate track stop/release;
- safe audio-track setting categories such as channel-count/sample-rate presence, without device IDs or labels.

### WebRTC and codec surface

- `RTCPeerConnection` construction;
- `RTCSessionDescription`/ICE API presence without gathering or persisting candidates;
- audio transceiver/sender/receiver capability surface;
- Opus support determined from standardized capability APIs when available, or from an in-memory local offer only if necessary; never export or persist SDP;
- track add/remove and connection-state event support;
- WebRTC stats API presence only, not a live network test.

### Cryptographic device trust

- `crypto.getRandomValues`;
- `crypto.subtle`;
- ability to generate the planned asymmetric key class in-browser;
- requested non-extractable key behavior;
- sign/verify or equivalent challenge operation;
- export refusal/behavior for the private key;
- no key material in exported results;
- an explicitly documented fallback investigation when non-extractable storage is unavailable.

Do not freeze the final production algorithm if browser evidence suggests a more compatible standards-based choice is needed. Record the algorithm tested and why.

### Storage and session transport

- IndexedDB open/write/read/delete using a random non-identifying fixture;
- cleanup of the temporary database/store;
- WebSocket constructor and secure `wss:` capability classification without contacting a production service;
- Page Visibility and lifecycle event presence;
- localStorage/sessionStorage presence only if useful for non-secret preferences; device private keys should not be placed there.

### Audio output and interaction

- `HTMLAudioElement`/media playback surface;
- `playsInline`/autoplay user-gesture behavior category;
- `setSinkId` presence as optional/degraded, never a phone requirement;
- pointer/touch events, viewport/safe-area CSS support, and orientation event surface;
- coarse accessibility features required by CP-033, without reading user accessibility settings.

## Probe UX and behavior

The page must be framework-free static HTML/CSS/JavaScript with no package manager, bundler, remote script, analytics, CDN, font, or image dependency.

Required UI:

- purpose/privacy statement;
- current secure-context status;
- **Run non-permission checks** button;
- **Test microphone permission** button with clear “no audio is recorded or sent” wording;
- visible step status and plain-language unsupported/degraded result;
- **Copy sanitized result** and **Download sanitized result** buttons;
- clear instruction for the user to return the JSON to the worker/Codex;
- no automatic test on page load beyond passive feature presence;
- no device/browser marketing claim.

The probe must work without JavaScript modules and should target a conservative syntax floor. Avoid optional chaining, top-level await, dynamic imports, WebAssembly, service workers, and framework polyfills unless the representative-device plan proves they are safe and necessary.

## Result schema

`mobile-capability-result.schema.json` must be a closed, bounded schema containing only:

- schema/probe version;
- generated timestamp UTC;
- user-supplied test label with a safe non-identifying slug;
- platform family: `ios`, `android`, `other`, `unknown`;
- browser engine/family: `webkit-safari`, `chromium`, `firefox`, `other`, `unknown`;
- coarse OS and browser major/minor version supplied/confirmed by the tester, with no full user agent;
- physical-device evidence boolean;
- secure-origin class: approved temporary HTTPS/local-development/unknown, never the live URL;
- each capability's present/absent/degraded/not-tested result and safe error category;
- microphone permission result and `tracks_stopped` boolean;
- non-extractable-key and IndexedDB cleanup booleans;
- probe duration/coarse timing;
- limitations/user-observed safe notes from a small enum or bounded allowlist;
- privacy review metadata.

Explicitly forbid full UA, model/device name, device ID/label, IP/MAC, hostname, URL, SDP, ICE candidate, key material, media samples, error stacks, raw output, free-form contact information, and storage contents.

## Device and browser sampling plan

`representative-device-plan.md` must define selection before results are collected:

1. Required family A: physical iPhone running Safari/WebKit.
2. Required family B: physical Android phone running current or realistically supported Chromium.
3. Creator's older phone: include when available as a compatibility data point.
4. Optional additional family: Android Firefox or another browser only when a physical test is actually available.

For each slot define:

- why it represents a meaningful lower/current boundary;
- whether the device is available;
- who will operate it;
- browser/OS version collection method that avoids a full UA dump;
- approved HTTPS delivery method;
- expected evidence file label;
- limitations.

Do not select a minimum supported OS from market share or memory. CP-035 freezes the support floor after the later call/interruption evidence.

## Temporary HTTPS delivery approval gate

The probe requires a secure context for meaningful microphone testing. Before it is opened on phones, the worker must present one bounded delivery proposal:

- exact mechanism and owner account;
- whether anything is installed/deployed;
- URL lifetime/stability class without publishing the URL;
- cost/billing implications;
- whether page access is public-by-address;
- confirmation that the page has no backend collection;
- cleanup/stop procedure;
- why it does not prejudge CP-040/CP-041's production provider decision.

Wait for explicit approval. If no mechanism is approved, return the built probe plus manual-blocker instructions and leave CP-030 In progress.

## Script requirements

### `Test-MobileCapabilityProbe.ps1`

- Static offline checks only; PowerShell 5.1 compatible.
- Confirm exactly the authorized local assets and no remote URLs/scripts/assets.
- Parse/inspect schema JSON.
- Check banned APIs/strings: analytics, MediaRecorder, full UA export, SDP/ICE result fields, device labels/IDs, network addresses, service worker, external fetch/XHR/beacon.
- Check that microphone access is behind the named click handler and every successful stream reaches a `finally`/cleanup track stop.
- Validate sample synthetic pass/degraded/unsupported objects in `.selftest-temp` and reject unknown/content-bearing fields.
- Confirm conservative syntax rules.
- Run twice and clean in `finally`.

### `Import-MobileCapabilityResult.ps1`

- Accept only a tester-supplied JSON file.
- Validate closed shape and safe enums/lengths.
- Run `Test-EvidencePrivacy.ps1` before copying atomically into `reports/results/`.
- Reject duplicate evidence labels, malformed JSON, full UA, model/device names, URLs/hostnames, addresses, SDP/ICE, device IDs, key material, content, and oversized payloads.
- Never edit a result to make it pass; return a precise safe rejection.

## Physical test procedure

For each approved phone/browser combination:

1. Tester confirms the intended browser and coarse OS/browser version.
2. Open the approved HTTPS link in the normal browser, not an embedded Telegram webview unless that webview is an explicit optional test.
3. Run non-permission checks.
4. Tap microphone test and choose allow/deny according to the planned case.
5. Confirm the page reports tracks stopped after the test.
6. Copy/download the sanitized JSON.
7. Close the page; no background test is claimed.
8. Return only the sanitized JSON to the worker.
9. Worker imports it through the validator and records one shared CP-004 harness result.

No remote worker may operate the phone or infer results from a screenshot. A screenshot may be used only for user troubleshooting and must not enter evidence if it contains personal UI.

## Capability matrix

`capability-matrix.md` must list every tested physical combination and every required capability as present/absent/degraded/not-tested. It must distinguish:

- actual physical observation;
- documentation-only expectation;
- desktop/synthetic self-test;
- blocker requiring CP-031 or a fallback investigation.

No row may say supported solely because documentation says an API exists.

## Verification and pass criteria

Codex may accept CP-030 only when:

- required capabilities and their rationale are documented;
- the probe is framework-light, static, private, and contains no telemetry/backend upload;
- static self-tests pass twice and clean all fixtures;
- the schema/importer reject sensitive and content-bearing data;
- microphone permission is user-initiated and streams stop immediately without recording;
- one real iOS Safari/WebKit and one real Android Chromium physical result are imported, or the checkpoint remains explicitly blocked rather than overclaiming;
- the creator's older phone is included when available, without redefining the whole target around it;
- every tested combination has present/absent/degraded results and named fallback investigations for blocking APIs;
- no background/30-minute-call/final-support claim is made;
- no provider resource was created without approval and cleanup;
- public repository status is unchanged during worker work.

## Failure and pause routes

- No physical iOS/Android device: leave CP-030 In progress and request a tester/device; do not accept emulation as equivalent.
- No approved HTTPS origin: leave the probe ready and request a bounded delivery approval.
- Missing required API: record degraded/unsupported and a fallback investigation; do not silently polyfill security or media features.
- Older phone cannot run the probe: preserve the result, then determine whether the syntax/API floor can be lowered without harming security; do not promise it.
- Unsafe result data: reject and rerun; never manually scrub a failing result into a passing claim without traceable regeneration.

## Worker handoff

Report:

1. Files created.
2. Required capability table.
3. Static self-test totals/exit codes.
4. Temporary HTTPS proposal and approval status.
5. Exact physical device/browser slots tested versus unavailable.
6. Imported sanitized result summaries.
7. Blocking/degraded APIs and fallback investigations.
8. Cleanup and privacy verification.

Do not mark CP-030 complete, commit, push, or start CP-031. Completion is left to Codex.
