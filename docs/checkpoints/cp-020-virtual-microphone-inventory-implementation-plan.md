# CP-020 Implementation Plan — Test Virtual Microphone and Licensing Inventory

> **Mandatory workflow:** Codex is the planner, technical reviewer, and checkpoint authority. Grok 4.6 in Cursor is the implementation worker. Grok must follow this bounded plan, must not mark the checkpoint complete, and must not commit or push. Codex independently reviews each stage. The worker must stop at the approval gate before installing, uninstalling, enabling, disabling, or changing any audio component.

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-020**  
Depends on: **CP-004 — Complete**  
Scope: **Read-only audio/option inventory followed by one explicitly approved reversible test-endpoint lifecycle**

## Objective

Select and prove one temporary virtual microphone endpoint for later Phase Zero injection tests while separately documenting viable production paths, licenses, administrator/restart requirements, signing, architecture support, repair/update responsibility, and uninstall behavior.

CP-020 does not prove PCM injection or Codex input, does not select the final production driver, and does not authorize redistribution. CP-021 owns injection. CP-026 owns the production-component ADR.

## Two-stage execution contract

### Stage A — read-only inventory and approval packet

Grok may perform Stage A immediately. It must not change devices or install software.

At the end of Stage A, Grok must stop and return an approval packet naming exactly one proposed temporary endpoint, its authoritative source, license/test-use status, package hash/version if a download is proposed, admin/reboot expectations, anticipated device changes, and rollback/uninstall steps.

### Stage B — approved lifecycle trial

Stage B is forbidden until:

1. Codex reviews the Stage A packet;
2. the user explicitly approves the named component and exact install/uninstall operation;
3. any admin prompt or restart requirement is explained before it occurs.

Approval for one candidate does not authorize a different package, background bundle, optional offer, permanent default-device change, reboot, or production redistribution. If the installer unexpectedly requires a reboot, bundled software, persistent service, license acceptance not in the packet, or a different device change, cancel and return for renewed approval.

CP-020 cannot become Complete until the approved endpoint is installed/activated, detected, removed/deactivated, and the prior audio state is verified restored. If the user does not approve Stage B, leave CP-020 In progress/Blocked—not failed—and do not unlock CP-021/CP-022.

## Working locations

The execution workspace is maintainer-local, private, and ignored by Git. Its absolute path is intentionally unpublished. All `work/` paths below are relative to that private workspace and are not public-repository artifacts.

Create or edit only:

```text
work/feasibility/audio/cp-020/
  README.md
  schema/
    audio-inventory.schema.json
    endpoint-lifecycle.schema.json
  scripts/
    Get-Cp020AudioInventory.ps1
    Test-Cp020AudioInventory.ps1
    Test-Cp020Restoration.ps1
  reports/
    audio-device-inventory.json
    virtual-microphone-option-matrix.md
    stage-a-approval-packet.md
    endpoint-lifecycle-result.json        # Stage B only
    restoration-comparison.json           # Stage B only
  cp-020-worker-report.md
```

The shared harness may create sanitized CP-020 result records in `work/feasibility/audio/results/`. Do not edit the public repository during worker work.

Public read-only sources:

- [`docs/plan.md`](../plan.md), [`docs/checkpoint-map.md`](../checkpoint-map.md), and [this CP-020 implementation plan](cp-020-virtual-microphone-inventory-implementation-plan.md);
- [`docs/security/threat-model-v0.md`](../security/threat-model-v0.md) and [`docs/security/data-flow-v0.md`](../security/data-flow-v0.md);
- official vendor/project license, install, signing, architecture, and uninstall documentation for evaluated candidates.

Private read-only sources, not included in Git:

- CP-002 environment inventory.
- CP-004 harness, schema, and privacy scripts.

## Mandatory safety boundaries

- Stage A is read-only. Do not install, uninstall, update, enable, disable, restart, reset, or reconfigure an endpoint.
- Do not change default input/output, communication defaults, per-app routing, volume, mute, enhancements, spatial audio, exclusive mode, sample rate, or Bluetooth routing.
- Do not restart Windows Audio, reboot Windows, change registry, create services/tasks, or request elevation in Stage A.
- Do not capture, play, synthesize, inject, record, or save audio. Endpoint enumeration is metadata-only.
- Do not open Codex Voice or change Codex microphone settings.
- Do not use NVIDIA Broadcast as proof of a bidirectional virtual cable unless authoritative evidence and later tests prove it supplies the required microphone sink. Installed does not mean suitable.
- Do not download binaries from mirrors, search-result ads, file-sharing sites, or unofficial releases.
- Do not commit installers, drivers, DLLs, licenses copied wholesale, device dumps, binaries, or vendor assets.
- Do not accept a license on the user's behalf without displaying the relevant terms/source and receiving approval when acceptance is required.
- Never claim “free,” “redistributable,” “open source,” or “production-safe” without an authoritative dated source.
- Do not persist device instance IDs, serial numbers, physical microphone names, usernames, exact paths, registry dumps, or raw PowerShell/PNP output.
- Any Stage B cleanup failure leaves CP-020 unaccepted and must be reported immediately with a safe recovery procedure.

## Stage A work

### 1. Sanitized audio inventory

Use supported read-only Windows APIs already present. Combine only what is needed from PnP/audio endpoint sources. Because CP-002's WASAPI listing was incomplete, implement a bounded fallback that can identify endpoint role/state without raw device dumps.

Persist only:

- endpoint category: render/capture;
- role: default multimedia/default communications/nondefault;
- class: physical, virtual, broadcast/effects, Bluetooth, HDMI/display, unknown;
- state: active/disabled/not-present/unknown;
- product label only when non-identifying and necessary for candidate detection;
- driver/provider product and semantic version when safe;
- architecture/signing/reboot/admin facts from authoritative metadata;
- default-role snapshot using internal safe labels, not raw endpoint IDs.

Record counts and safe labels. Keep raw endpoint IDs and exact PnP values in memory only and discard them.

### 2. Candidate matrix

Evaluate at least these strategy classes, not necessarily specific brands if no authoritative candidate exists:

- separately installed documented third-party virtual cable;
- third-party component with explicit redistribution agreement;
- Windows/Microsoft sample or first-party driver path requiring build/signing;
- project-maintained open-source virtual audio driver;
- already-installed effects/broadcast device, only if it truly accepts programmatic microphone injection.

For each credible candidate record:

- authoritative product/project URL and documentation date;
- license identifier/terms link and commercial/personal/test/redistribution distinction;
- download/signature/hash availability;
- Windows architectures and supported versions;
- admin/elevation requirement;
- reboot requirement;
- services/drivers/endpoints created;
- input sink/output source topology;
- programmatic PCM feed mechanism, if documented;
- headless/silent install availability and whether it is allowed;
- uninstall/repair/update behavior;
- known conflicts and support burden;
- suitability: test-only candidate, production candidate to investigate, unsuitable, or unknown;
- evidence provenance: official documentation, signed package metadata, observed locally, or inference.

Use primary official sources. Pricing, licensing, and availability are time-sensitive; record an `as of` date. Do not rely on blog summaries for decisive license claims.

### 3. Candidate selection policy

The temporary test endpoint must satisfy all mandatory gates:

- authentic official source and verifiable package identity;
- legal personal feasibility testing on this machine;
- no project redistribution required;
- supports the host architecture/Windows version;
- exposes the microphone-side topology needed for later PCM injection;
- reversible uninstall/deactivation procedure;
- expected device/default changes are knowable;
- no silent bundle or unrelated product requirement;
- no mandatory persistent account/cloud service for the local audio path;
- admin/reboot impact is disclosed.

Rank passing candidates deterministically by: least system mutation, cleanest uninstall, strongest licensing clarity, lowest support burden, then best documented injection interface. Free-form model preference is not a selection rule.

### 4. Stage A approval packet

`stage-a-approval-packet.md` must state:

- proposed component and exact version/source;
- why it won under the deterministic policy;
- test-only versus production status;
- exact installer/download command or manual action proposed;
- expected hash/signature verification;
- license/terms acceptance required;
- admin and reboot requirements;
- devices/services/files expected to be added;
- pretrial state to snapshot;
- exact uninstall/deactivation and restoration steps;
- what constitutes automatic abort;
- whether a restart would require a separate approval;
- confirmation that no audio will be captured or injected in CP-020.

Stop after creating the packet. Do not pre-download an installer unless Codex/user approval explicitly includes that download.

## Stage B work after explicit approval

### 1. Preflight and restoration snapshot

- Re-run sanitized inventory.
- Confirm the selected version/source/hash still matches the packet.
- Capture default capture/render and communication-role state using safe internal handles kept only as long as restoration requires.
- Confirm no active remote Voice/media session.
- Confirm the chosen endpoint is not already present in a conflicting state.
- Set a cleanup plan before elevation/install.

### 2. Install or activate exactly one approved test endpoint

- Use the approved official installer/method only.
- Allow the user to handle elevation/license UI; do not bypass UAC.
- Decline optional bundles, telemetry, startup items, or unrelated components unless explicitly required and approved.
- Do not reboot automatically.
- Record sanitized lifecycle states and coarse durations, never raw installer logs.

### 3. Verify endpoint topology without audio

- Confirm the expected capture/render endpoint pair/classes appear.
- Confirm state is active and usable for later CP-021/CP-022 work.
- Confirm existing defaults did not change; if they changed unexpectedly, abort and restore.
- Do not feed or capture audio.

### 4. Remove/deactivate and restore

- Uninstall/deactivate using the approved procedure.
- Confirm only project-created/trial component state is removed.
- Verify pretrial default roles/settings match the snapshot.
- Confirm existing endpoints remain usable and the trial endpoint is absent or safely inactive.
- Detect a pending reboot. If required for full removal, pause and request approval before reboot; CP-020 remains In progress until post-reboot verification.

## Schema and script requirements

### `audio-inventory.schema.json`

Closed, bounded schema with no device IDs, serials, paths, raw output, audio, or content. Include snapshot version, OS/audio subsystem class, endpoint counts/safe categories, default-role safe labels, installed virtual-component safe product/version facts, limitations, source classification, and privacy review.

### `endpoint-lifecycle.schema.json`

Closed state sequence:

- `not_started`, `preflight`, `approved`, `installing`, `detected`, `removing`, `restoring`, `verified_restored`, `failed`, `cleanup_failed`, `reboot_pending`;
- expected/observed component class and version;
- admin/reboot booleans;
- defaults-changed boolean;
- cleanup state and safe error category;
- coarse durations;
- no audio or raw logs.

### `Get-Cp020AudioInventory.ps1`

- PowerShell 5.1 compatible, read-only, standard APIs only.
- Bounded exact queries; no raw dump persistence.
- Normalize/redact before serialization.
- Atomic JSON write under `reports/` after privacy filtering.
- Nonzero exit on unsafe failure.

### `Test-Cp020AudioInventory.ps1`

- Synthetic fixtures only under `.selftest-temp`.
- Reject endpoint IDs, serials, paths, raw PnP output, user labels, audio/media filenames, unknown fields, oversized collections, and content.
- Prove deterministic classification and privacy-filter integration.
- Run twice and clean in `finally`.

### `Test-Cp020Restoration.ps1`

- Stage A: validate snapshot comparison logic using synthetic safe fixtures only.
- Stage B: compare sanitized pre/post state after uninstall.
- Never change settings itself.
- Fail if defaults differ, expected endpoint remains active unexpectedly, cleanup is incomplete, or state is unknown.

## Evidence recording

Use the shared CP-004 recorder for separate sanitized results:

- Stage A inventory/selection result;
- Stage B install/detect result;
- Stage B remove/restore result.

Result notes must state test-only status and must not claim injection or process capture. Evidence references must be safe relative paths.

## Pass criteria

Codex may accept CP-020 only when:

- the inventory is reproducible and privacy-safe;
- authoritative licensing/redistribution/admin/reboot/update/uninstall facts are recorded for credible options;
- test dependency and possible production dependency are clearly separated;
- one explicitly approved test endpoint completes install/detect/remove or activate/detect/deactivate;
- prior default audio state is captured and verified restored;
- no unauthorized binary is committed or redistributed;
- no audio is recorded, injected, or captured;
- all temporary state is cleaned or an approved reboot is completed and re-verified;
- the public repository remains unchanged during worker work.

## Failure and pause routes

- No suitable candidate: investigate a documented Microsoft sample/driver path; do not fake injection through speakers.
- License unclear: mark candidate unknown/unsuitable until authoritative clarification.
- User declines install/admin/reboot: CP-020 pauses without failure.
- Unexpected bundle, reboot, service, or default change: abort, restore, and request new approval.
- Cleanup cannot be proven: mark cleanup failed, do not advance CP-021/CP-022, and provide a safe manual recovery plan.

## Worker handoff

Stage A handoff must report the approval packet and stop. Stage B final handoff must report:

1. Files created/changed.
2. Read-only inventory methods.
3. Candidate matrix and authoritative sources.
4. Exact approval received and exact lifecycle action performed.
5. Before/after state and restoration result.
6. Self-test totals and shared-harness results.
7. Any admin/reboot/license/cleanup limitation.

Do not mark CP-020 complete, commit, push, or start CP-021/CP-022. Completion is left to Codex.
