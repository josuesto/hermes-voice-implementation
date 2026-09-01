# CP-010 Implementation Plan — Codex Installation, Process, Package, and Protocol Discovery

> **Mandatory workflow:** Codex is the planner, technical reviewer, and checkpoint authority. Grok 4.6 in Cursor is the implementation worker. Grok must follow this bounded plan, must not mark the checkpoint complete, and must not commit or push. Codex independently reviews the files and reruns the safe checks. Only after acceptance does Codex update status and publish one public-safe checkpoint commit.

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-010**  
Depends on: **CP-004 — Complete**  
Scope: **Read-only discovery of the installed Codex desktop surface; no Codex control action**

## Objective

Build a reproducible, privacy-preserving map of how the installed Windows Codex desktop app can be identified and observed. Determine which candidate control surfaces exist—documented interface, registered protocol, package activation, semantic Windows UI Automation, keyboard command, or optional vision—without invoking unknown routes, changing the active task, starting Voice, sending keys, clicking controls, or treating an undocumented observation as a stable contract.

This checkpoint answers “what surfaces exist and how confidently can we detect them?” It does **not** prove deterministic launch, task enumeration, task selection, or Voice control; those belong to CP-011 through CP-016.

## Working locations

The execution workspace is maintainer-local, private, and ignored by Git. Its absolute path is intentionally unpublished. All `work/` paths below are relative to that private workspace and are not public-repository artifacts.

Create or edit only the authorized CP-010 files listed below under:

`work/feasibility/codex-control/cp-010/`

Public read-only sources:

- [`docs/plan.md`](../plan.md)
- [`docs/checkpoint-map.md`](../checkpoint-map.md)
- [This CP-010 implementation plan](cp-010-codex-surface-discovery-implementation-plan.md)
- [`docs/security/threat-model-v0.md`](../security/threat-model-v0.md)
- [`docs/security/data-flow-v0.md`](../security/data-flow-v0.md)

Private read-only sources, not included in Git:

- CP-002 environment inventory.
- CP-004 harness documentation, result schema, result recorder (`New-FeasibilityResult.ps1`), and privacy filter (`Test-EvidencePrivacy.ps1`).

The implementation repository remains documentation-only during worker execution. Do not edit it.

## Mandatory safety and privacy boundaries

- Do not close, restart, launch, focus, minimize, foreground, or otherwise manipulate Codex.
- Do not invoke `codex://` links. Enumerate only registered handler/manifest information that already exists.
- Do not click, invoke, select, expand, scroll, type into, or send keyboard shortcuts to any Codex control.
- Do not create, rename, open, archive, delete, or inspect the contents of any Codex task.
- Do not start or stop Codex Voice, change microphone permissions, or touch audio devices.
- Do not read or persist prompts, task bodies, responses, transcripts, task titles, project paths, account details, cookies, tokens, local account databases, browser storage, or OpenAI credentials.
- Do not dump entire registry branches, package manifests, process command lines, UIA trees, window text, environment variables, or raw command output.
- Do not inspect network traffic, open ports, IPC payloads, memory, databases, executable strings, or private application files.
- Do not decompile, disassemble, patch, inject into, hook, or reverse engineer the Codex executable.
- Do not install dependencies or request administrator privileges.
- Do not use screenshots, OCR, screen coordinates, or computer vision in this checkpoint.
- If the current Codex process/window is absent, record `dependency_missing` and stop the live-window/UIA portion. Do not launch it; CP-011 owns launch behavior.
- All persisted evidence must be sanitized, content-free, and pass `privacy-policy-1.0.0`.

## Authorized files

Create exactly this private tree:

```text
work/feasibility/codex-control/cp-010/
  README.md
  schema/
    codex-surface-report.schema.json
  scripts/
    Get-CodexSurfaceDiscovery.ps1
    Test-CodexSurfaceDiscovery.ps1
  reports/
    codex-surface-report.json
    codex-adapter-capability-matrix.md
  cp-010-worker-report.md
```

The existing shared harness may create one sanitized CP-010 result JSON in:

`work/feasibility/codex-control/results/`

Do not create raw dumps or additional persistent files. Any test fixtures must live under `work/feasibility/codex-control/cp-010/.selftest-temp` and be removed in `finally`.

## Discovery model

### 1. Package and installation identity

Use supported, read-only Windows package/application-registration APIs. Prefer exact known package/application registrations from the private CP-002 inventory over broad enumeration.

Record only sanitized fields such as:

- package kind: packaged/MSIX, unpackaged, or unknown;
- package/application family label after generic normalization;
- semantic version string;
- architecture class;
- registered activation method class;
- presence of a signed publisher identity as a boolean or generic publisher label;
- observed/absent/unknown status.

Never persist install paths, user profile paths, package storage paths, publisher IDs that identify the user, raw manifest XML, or arbitrary application lists.

### 2. Process and window identity

Observe only the existing Codex process tree. Record normalized process image basenames/roles, parent-child role relationships, packaged app identity, top-level window presence, generic window class, and visibility/state categories.

Do not persist:

- PIDs or handles;
- process command lines;
- usernames/session tokens;
- full executable paths;
- window titles or task names;
- text from child controls.

Repeat observation at least three times in the same non-mutating run and classify fields as stable, volatile, or unavailable.

### 3. Registered `codex://` protocol

Read only the exact registered protocol handler and relevant application manifest declaration. Normalize the result to:

- registered: true/false;
- registration scope: per-user/system/package/unknown;
- activation target class: packaged activation, executable command, or unknown;
- executable basename only when safely derivable;
- declared route/verb names only if explicitly present in installed manifest or official documentation already available locally;
- source classification: documented, registered/observed, or inferred.

Do not invoke the handler, guess route names, fuzz URLs, enumerate secrets embedded in command templates, or persist raw registry values. If a command template contains a path, arguments, or user data, transform it in memory to a generic shape and discard the raw value.

### 4. Semantic UI Automation structure

Use read-only Windows UI Automation against the current Codex top-level window only. Traverse with a strict node/depth/time limit. Query properties only; never request or invoke action patterns.

Allowed persisted information:

- fixed application-shell control roles;
- generic `ControlType` values;
- stable `AutomationId`/class names only after privacy screening;
- presence of fixed semantic labels such as New task or Voice when they are clearly application controls rather than task content;
- whether selection, invoke, toggle, or value patterns are advertised, recorded only as booleans;
- dynamic/content region present: true/false, with its values redacted.

Dynamic names, task titles, project paths, prompt text, response text, usernames, and accessibility values must be replaced with categories such as `dynamic-content-redacted` before any object leaves memory. If reliable redaction cannot be guaranteed, skip the subtree and record `redaction_not_provable`.

### 5. Candidate control-surface ranking

Rank candidates in this fixed order:

1. officially documented supported local/API control;
2. explicitly registered and safely testable deep link/native activation;
3. semantic UI Automation with stable identity/state signals;
4. stable keyboard command with independent state verification;
5. optional vision/OCR assistance as a last-resort future adapter.

For each candidate, record:

- capability: detect, launch, enumerate tasks, create task, open task, start Voice, stop Voice, verify state;
- status: observed, not observed, unknown, or out of scope;
- confidence: documented, registered/observed, or inferred;
- mutation required to prove: yes/no;
- owning next checkpoint;
- privacy/reliability risk;
- why it is or is not allowed to advance.

Do not mark a capability supported merely because a control label or protocol registration exists.

## Report schema

`codex-surface-report.schema.json` must be closed with `additionalProperties: false`, bounded arrays/string lengths, safe enums, and no content-bearing fields. It must cover:

- schema version and checkpoint;
- run timestamp UTC;
- discovery script version;
- installed/present/absent/unknown package state;
- normalized package/version/architecture facts;
- normalized process-role and window-class observations;
- protocol registration facts;
- bounded semantic UIA capability observations;
- candidate control paths and evidence classification;
- redaction/skip counts, never values;
- limitations and error categories;
- privacy policy result.

Explicitly forbid fields named or equivalent to `path`, `command_line`, `window_title`, `task_title`, `prompt`, `task_content`, `response`, `transcript`, `token`, `cookie`, `raw_output`, `uia_dump`, or `registry_dump`.

## Script requirements

### `Get-CodexSurfaceDiscovery.ps1`

- PowerShell 5.1 compatible, standard PowerShell/.NET only.
- Read-only and noninteractive.
- Use exact process/package scoping; never scan arbitrary application content.
- Build a sanitized object in memory, validate it against explicit shape rules, pass it through `Test-EvidencePrivacy.ps1`, then write atomically under `reports/`.
- Refuse overwrite unless `-Force` is explicitly supplied for the same safe report path; the worker should normally remove only its own prior CP-010 report before a rerun.
- Return a small status object and a nonzero exit on unsafe/unhandled failure.
- Use `try/finally` for temporary state.
- Never echo raw registry/UIA/process values on failure.

### `Test-CodexSurfaceDiscovery.ps1`

- Use only synthetic fixtures under `.selftest-temp` for shape/redaction tests.
- Prove content-bearing fields, paths, command lines, task titles, deep-link payloads, raw UIA trees, oversized collections, and unknown properties are rejected.
- Prove dynamic UIA text becomes only a redaction count/category.
- Prove protocol normalization never returns raw command templates.
- Prove an absent Codex process produces a safe `dependency_missing`/partial report without launching Codex.
- Prove repeated sanitized output is deterministic apart from timestamp/observed volatile categories.
- Clean all fixtures in `finally` and emit total/passed/failed/cleanup plus exit code.

## Execution sequence

1. Validate the authorized tree and read the CP-004 harness instructions.
2. Implement schema and synthetic self-test first.
3. Run the synthetic self-test twice.
4. Run the read-only discovery script against the existing host state once.
5. Run it twice more without changing Codex state; compare normalized identities.
6. Parse and privacy-filter the final JSON.
7. Write the capability matrix from sanitized findings only.
8. Use the shared CP-004 recorder to create one CP-010 result with:
   - `action=discover-codex-surface`
   - observed safe state category;
   - duration;
   - result and error category;
   - cleanup state `not_required` or `completed`;
   - safe relative references to the CP-010 reports.
9. Confirm no task/control mutation occurred and write the worker report.

## Verification and acceptance evidence

Before handoff, the worker must prove:

- all authorized files exist and parse;
- the synthetic self-test passes twice with cleanup completed;
- the live discovery completes without interacting with Codex;
- package version, normalized process roles, top-level window identity, and protocol registration are consistently detected or explicitly unavailable across three observations;
- UIA collection is bounded and contains no dynamic text or task content;
- protocol evidence is registration-only and no link was invoked;
- capability ranking distinguishes documented, observed, and inferred findings;
- the final report and shared result pass the privacy filter;
- no raw paths, command lines, task titles, prompts, responses, transcripts, tokens, UIA dumps, screenshots, or private application files exist in the CP-010 tree;
- `.selftest-temp` is absent;
- public repository status is unchanged.

## Pass criteria

Codex may accept CP-010 only when:

- the installed Codex version and normalized package/process/window identities are repeatably detected or a precise supported manual prerequisite is documented;
- the registered protocol handler is characterized without being invoked;
- UIA findings are semantic, bounded, content-free, and non-mutating;
- every candidate path is ranked with documented/observed/inferred provenance;
- no later capability is falsely claimed proven;
- all evidence is reproducible and privacy-safe.

## Failure route

If Codex cannot be detected reliably, stop the automation track and document the exact manual prerequisite. If privacy-safe UIA inspection cannot be guaranteed, omit UIA rather than capture content. If only fragile screen coordinates or unverified inference remain, record that finding and do not advance that path.

## Worker handoff

Report:

1. Files created.
2. Exact read-only commands/APIs used.
3. Three-run stability findings.
4. Protocol/UIA/candidate matrix summary.
5. Synthetic self-test totals and exit codes.
6. Privacy/redaction verification.
7. Limitations, blockers, and which surfaces CP-011/CP-012 may test next.

Do not mark CP-010 complete, commit, push, or start CP-011/CP-012. Completion is left to Codex.
