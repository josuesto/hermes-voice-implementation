# CP-011 Implementation Plan — Deterministic Codex Launch and Windows Session Control

> **Mandatory workflow:** Codex is the planner, technical reviewer, and checkpoint authority. Grok 4.6 in Cursor is the implementation worker. Grok must follow this bounded plan, must not mark the checkpoint complete, and must not commit or push. Codex independently reviews each stage. The worker must stop at every approval gate before launching, focusing, minimizing, closing, or otherwise changing the Codex desktop app.

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-011**  
Depends on: **CP-010 — Complete**  
Scope: **Prove deterministic desktop-app activation/reuse and current unlocked Windows-session ownership without opening, creating, selecting, reading, or changing any Codex task and without starting Voice**

## Objective

Prove that a Windows companion can:

1. recognize whether the installed Codex desktop app is absent, already visible, backgrounded, or minimized in the current interactive Windows session;
2. activate or reuse exactly the intended store-signed package instance through one explicitly approved route;
3. distinguish process start from a usable, responsive desktop shell;
4. verify that the observed app belongs to the current awake, unlocked user session without persisting a username, SID, PID, command line, window caption, task title, prompt, or conversation content;
5. time out and fail closed when ownership, readiness, foreground state, or cleanup cannot be proved.

CP-011 does **not** enumerate recent tasks, create a task, resume a task, inspect task content, start or stop Voice, choose a microphone, use keyboard navigation, or use screenshots/OCR. CP-012 owns privacy-safe task enumeration and stable identity. CP-013 owns exact task creation/opening. CP-014 owns Voice.

## Architectural correction from current official documentation

As of 2026-09-01, [official OpenAI documentation](https://learn.chatgpt.com/docs/app-server) describes **Codex App Server** as the documented interface Codex uses to power rich clients, including authentication, conversation history, approvals, streamed events, and thread/session operations such as `thread/start`, `thread/resume`, `thread/list`, and `thread/read`.

The same documentation does not state that App Server launches, focuses, or controls the Windows desktop UI, nor that the registered `codex://` handler is a supported desktop automation contract. Therefore:

- App Server is the preferred documented future **thread/session control plane**, but it is not desktop-launch proof.
- CP-011 may confirm App Server/CLI availability and document the boundary, but it must not call `thread/start`, `thread/resume`, `thread/list`, or another thread method.
- Desktop activation remains a Windows/package feasibility experiment.
- Registration of `codex://` remains observation only until a separately approved invocation trial proves the exact behavior.
- No undocumented route, query parameter, task ID, prompt, or payload may be guessed.

If official documentation changes during execution, record the exact official URL, access date, and what changed. Do not silently expand scope.

## Three-stage execution contract

### Stage A — non-mutating harness, official-interface assessment, and approval packets

Grok may perform Stage A immediately. Stage A may read the accepted CP-010 artifacts, current official OpenAI documentation, exact package metadata, current process/window state, current Windows session state, and command help/version output.

Stage A must not:

- launch, activate, focus, minimize, restore, close, restart, or kill Codex;
- invoke `codex://`;
- start an App Server listener or send App Server requests;
- create/resume/list/read a Codex thread;
- click, invoke UIA actions, send keys, capture screenshots, or use OCR;
- lock, sleep, wake, or unlock Windows.

Stage A ends with two separate approval packets and then stops.

### Stage B — approved already-running reuse/focus trials

Stage B is forbidden until Codex reviews Stage A and the user explicitly approves the exact actions. The approval must name:

- selected activation route;
- whether foreground focus, restore-from-minimized, and temporary minimize operations are included;
- expected visible disruption;
- number and distribution of trials;
- timeout/abort behavior;
- confirmation that no task or Voice operation will occur.

Stage B may run only while Codex is already open. It must never close a pre-existing Codex instance. It proves idempotent reuse and foreground/readiness behavior.

### Stage C — approved cold-launch trials

Stage C is separately forbidden until:

1. Stage B is independently accepted by Codex;
2. the user confirms no Codex turn, terminal, file operation, review, Voice session, or unsaved interaction is active;
3. the user understands that Codex desktop will be closed and relaunched repeatedly while Cursor remains the worker host;
4. the user explicitly approves the exact graceful-close and launch route, ten trials, timeout, and final-state behavior.

The active Codex reviewing task must not be relied upon during Stage C. The Cursor worker writes resumable evidence to disk, and the user returns to Codex after the final relaunch.

No approval permits force-killing processes, unlocking Windows, waking a sleeping machine, changing task state, invoking an unapproved protocol URI, or falling back to another route.

## Candidate order

Evaluate and choose deterministically:

1. **Documented App Server boundary** — record whether an installed `codex` CLI exposes documented `app-server` help/version. This is not a desktop launch route and cannot win desktop activation.
2. **Windows packaged application activation** — activate the exact installed MSIX application identity/AUMID using a bounded Windows packaged-app activation API. This is the preferred desktop launch experiment because it targets the already verified package and carries no guessed URI payload.
3. **Registered base protocol activation** — test only the exact registered base `codex://` route, with no host, path, query, fragment, task ID, or prompt. This requires a new Codex review and explicit user approval if packaged activation fails or is unavailable.
4. **Semantic UI Automation for existing-window focus/readiness only** — allowed after approval for restore/focus and positive shell-readiness evidence. It must not discover or invoke task/Voice controls.
5. **Keyboard and vision/OCR** — out of scope for CP-011 and must not be used.

Do not automatically fall through from one mutating route to another. Each new route requires an updated approval packet, Codex review, and user approval.

## Working locations

Worker planning and evidence remain private and are not committed to this public repository. Use the repository-neutral private workspace:

`work/feasibility/codex-control/cp-011/`

Create or edit only:

```text
work/feasibility/codex-control/cp-011/
  README.md
  schema/
    launch-observation.schema.json
    launch-trial-set.schema.json
  scripts/
    Get-Cp011LaunchPreflight.ps1
    Test-Cp011LaunchHarness.ps1
    Invoke-Cp011OpenInstanceTrials.ps1       # Stage B only
    Invoke-Cp011ColdLaunchTrials.ps1         # Stage C only
  reports/
    official-interface-assessment.md
    launch-candidate-matrix.md
    stage-b-approval-packet.md
    stage-c-approval-packet.md
    open-instance-trials.json                # Stage B only
    cold-launch-trials.json                  # Stage C only
    launch-state-matrix.md                    # Stages B/C
    timing-and-failure-summary.md             # Stages B/C
  cp-011-worker-report.md
```

The shared CP-004 harness may create sanitized CP-011 records under:

`work/feasibility/codex-control/results/`

Do not edit the public repository during worker execution. Do not create product code, installers, scheduled tasks, services, startup entries, registry values, shortcuts, or provider resources.

## Mandatory safety and privacy boundaries

- Use only the exact store-signed package identity accepted in CP-010. Do not launch an arbitrary executable path from inventory text.
- Never store or print usernames, SIDs, raw session tokens, PIDs, handles, command lines, package install paths, window captions, UIA names, AutomationIds, task titles, project paths, prompts, thread IDs, or conversation content.
- Normalize session evidence to `current-interactive-session-match`, `different-session`, `no-interactive-session`, or `unknown`.
- Normalize process/window evidence to the CP-010 roles and categorical window identity only.
- Do not read or write clipboard content.
- Do not pass any content in a URI, command-line argument, environment variable, window message, or UIA value.
- Do not call App Server thread methods, even read-only listing methods; CP-012 owns thread enumeration.
- Do not use `Start-Process` against the package executable path. Use the reviewed packaged activation adapter or separately approved base protocol adapter.
- Do not use `Stop-Process`, `taskkill`, package termination APIs, service control, or forced process-tree teardown.
- Graceful close in Stage C may target only the exact main window verified as launched/reused by the current trial, in the current interactive session, after approval. If graceful close fails, stop the sequence; do not escalate.
- Do not close a Codex instance that existed before the Stage C run unless the user explicitly approved that exact initial close after confirming no active work.
- Never attempt to unlock Windows, synthesize credentials, wake from sleep, change power settings, create a scheduled task, or run as another user/session.
- Do not test a real crash by killing or corrupting Codex. Crash/early-exit handling is synthetic plus passive observation only.
- Do not alter Codex settings, model, reasoning level, sandbox, permissions, project, thread, task, terminal, or Voice.
- Do not take screenshots, save audio, or capture window pixels.
- A new process is not readiness. A visible window alone is not task readiness. Readiness here means only a responsive application shell.
- Any unexpected prompt, sign-in screen, update flow, task mutation, Voice state, error requiring user choice, duplicate UI instance, or unrelated window must stop the live sequence.

## Stage A work

### 1. Reconcile accepted CP-010 evidence

Read the CP-010 accepted review, canonical sanitized report, capability matrix, and worker report. Carry forward only:

- exact package presence through an internal handle;
- normalized process roles;
- normalized top-level window class category;
- packaged activation classification;
- registered base protocol and `invoked=false` history;
- UIA volatility and its non-capability status.

Do not copy private package paths, version-specific identifiers, raw protocol templates, or UIA values into new reports.

### 2. Current official-interface assessment

Use current official OpenAI documentation only for product-interface claims. Record:

- App Server is documented for rich client integrations and thread/session operations;
- stdio is the documented default transport;
- WebSocket is marked experimental/unsupported in the current documentation;
- App Server does not document desktop-window launch/focus;
- no official desktop deep-link route for launch/focus was located.

If an installed `codex` command is available, Stage A may run only bounded help/version commands that cannot start a listener or thread, such as exact version and `app-server --help`. Record availability and documented capability categories, not executable paths or full help dumps. Do not install or update the CLI.

### 3. Launch preflight

Implement a read-only preflight returning only sanitized categorical state:

- package: present/absent/ambiguous;
- current Windows session: active-unlocked/locked-or-disconnected/no-interactive-session/unknown;
- power/display prerequisite: awake-and-interactive/unsupported/unknown;
- Codex main UI: absent/visible/minimized/background/ambiguous;
- normalized current-session ownership: match/different/unknown;
- duplicate main UI: no/yes/unknown;
- readiness evidence available: yes/no/partial;
- approval token present: no/yes, where the token is an in-memory test authorization flag rather than a secret.

Use Windows session APIs that distinguish the current interactive session without persisting identity. If lock/sleep state cannot be proved safely, return `unknown` and refuse activation.

### 4. Readiness contract

Define positive shell readiness as all of:

1. exact accepted package role observed in the current interactive session;
2. exactly one intended main UI identity or an explicitly documented single reused instance;
3. categorical top-level window present and visible after any approved restore;
4. window responds to a bounded non-content liveness query;
5. UIA root/control view is readable within the CP-010 node/depth/privacy bounds;
6. the same normalized identity remains stable for at least three consecutive polls;
7. no unexpected sign-in/update/error/user-choice state is detected through categorical evidence;
8. timeout has not expired.

This contract must be named `shell-ready`, never `task-ready` or `voice-ready`.

Use a default poll interval of 250 ms, shell-readiness timeout of 45 seconds, graceful-close timeout of 20 seconds, and stabilization window of three polls. These values must be constants in the harness and recorded in the approval packets. Changing them requires re-review.

### 5. State machine

Implement and document:

```text
preflight
  -> refused-unsupported-session
  -> refused-approval-missing
  -> already-ready
  -> activation-requested
      -> process-observed
      -> shell-observed
      -> shell-ready
      -> timeout
      -> ambiguous-instance
      -> unexpected-state
      -> exited-early
```

Cleanup is separate:

```text
not-owned -> never-close
owned-by-current-trial -> graceful-close-requested -> closed | close-timeout
```

Never convert `close-timeout` into forced termination.

### 6. Candidate matrix and selection

For each candidate record:

- official/documented, Windows-documented, observed, or inferred provenance;
- exact capability: thread control, desktop activation, reuse, focus, readiness, or cleanup;
- mutating action required;
- user-visible disruption;
- content exposure risk;
- current-session verification strength;
- success evidence;
- failure/abort evidence;
- later checkpoint owner;
- whether it can advance now.

Select packaged application activation first when its exact package application identity can be derived from current package metadata without a persisted personal path. The base protocol is a fallback only. App Server must not be misranked as desktop activation.

### 7. Synthetic harness tests

The Stage A self-test must use fixtures/simulators only and must prove at least:

- missing approval refuses before activation;
- package absent/ambiguous refuses;
- locked/disconnected/no-interactive/unknown session refuses;
- sleeping/unknown interactive prerequisite refuses;
- different/unknown session ownership refuses;
- already-ready returns without a second activation;
- background/minimized state requires the approved focus/restore capability;
- process start without a shell times out;
- visible shell without stable liveness does not pass;
- three stable polls produce `shell-ready`;
- duplicate/ambiguous main UI fails closed;
- unexpected sign-in/update/error/user-choice state aborts;
- exited-early and crash-observed states are distinct;
- pre-existing instance is never closed by cleanup;
- trial-owned instance receives graceful close only;
- close timeout never escalates to force kill;
- protocol registration never counts as invocation success;
- App Server thread support never counts as desktop launch proof;
- raw content-bearing fields are rejected or redacted before persistence;
- unknown fields, invalid enums/types/bounds, outside destinations, and unsafe evidence references fail closed;
- failed tests leave no final/temp evidence.

Run the synthetic suite twice. Stage A is not ready for review until both runs have zero failures and complete cleanup.

### 8. Approval packets

`stage-b-approval-packet.md` must state:

- exact selected activation/reuse route and why;
- exact already-open trial distribution totaling ten;
- whether temporary minimize/restore and foreground focus are included;
- visible disruption and duration;
- readiness/ownership criteria;
- abort conditions;
- confirmation that Codex will not be closed;
- confirmation that no task/Voice action occurs.

`stage-c-approval-packet.md` must state:

- exact selected route and exact graceful-close method;
- that the active Codex desktop task may be interrupted while Cursor continues;
- requirement for the user to confirm no active work/Voice/terminal/review;
- ten cold-launch trials;
- how the initial closed state is created;
- how only a trial-owned verified window is gracefully closed between trials;
- that failure to close stops the sequence without force kill;
- final state: leave Codex open and shell-ready;
- recovery instructions if Codex does not relaunch;
- explicit statement that no task/thread/Voice operation occurs.

Stop after Stage A and return both packets to Codex. Do not run Stage B or C.

## Stage B work after explicit approval

### 1. Already-open trial matrix

Run ten consecutive trials using the approved route. The approved packet must define a deterministic distribution that includes:

- already visible/ready reuse;
- background but not minimized;
- minimized then approved restore;
- repeated activation while already ready.

For each trial persist only:

- trial number and categorical starting state;
- route category;
- whether a new activation request was issued;
- reuse/new-main-ui/ambiguous result;
- current-session match;
- shell-ready yes/no;
- foreground granted/not-required/not-granted/unknown;
- duration measurements;
- timeout/error category;
- cleanup state `not_required`.

Pass only if all ten reuse the correct current-session app, no duplicate main UI is created, shell readiness is positively proved, and no task/Voice state changes.

### 2. Focus requirement conclusion

Separate:

- activation/reuse success;
- shell readiness;
- foreground focus.

If Windows refuses foreground focus but the correct shell is visible/responsive, record `focus-not-granted`; do not fake input or use keyboard workarounds. State whether later semantic UIA can operate without foreground focus. Do not test task controls here.

### 3. Stage B stop

After ten trials, stop and return evidence to Codex. Stage C remains forbidden until Stage B is accepted and the user gives the separate cold-launch approval.

## Stage C work after explicit approval

### 1. Cold-state preflight

Immediately before the sequence:

- re-run preflight;
- obtain the user’s recorded confirmation of no active Codex work;
- confirm Cursor is the worker host and evidence path is writable;
- confirm the exact activation and graceful-close methods match the approval;
- confirm Windows is awake/unlocked/current-session match;
- abort on any unexpected state.

### 2. Ten consecutive cold launches

For each trial:

1. prove the main UI is absent in the current session;
2. request activation once through the approved route;
3. observe normalized process/window transitions;
4. require `shell-ready` within 45 seconds;
5. prove current interactive-session ownership and absence of an ambiguous duplicate;
6. record sanitized timing/error evidence;
7. for trials 1–9, gracefully close only the exact trial-owned verified main window;
8. require closed state within 20 seconds or stop without force kill;
9. for trial 10, leave Codex open and shell-ready.

Do not interact with the newly visible task/chat surface. Do not dismiss prompts or choose a workspace. An unexpected setup/sign-in/update/error state aborts for user review.

### 3. Passive crash/early-exit handling

Do not induce a crash. If the approved activation process exits before shell readiness, record `exited-early`. If the verified shell disappears unexpectedly, record `unexpected-exit`. Preserve the previous valid evidence and stop.

### 4. Unsupported locked/sleeping conditions

Do not lock or sleep the machine. Completion requires:

- synthetic proof that locked/disconnected/sleeping/unknown states refuse before activation;
- live preflight proof that the supported run occurred only while awake and unlocked;
- documentation that locked/sleeping operation is unsupported by product contract.

## Evidence model and privacy

Use closed Draft 2020-12 schemas with `additionalProperties: false` throughout. Use the CP-004 recorder and `privacy-policy-1.0.0` fail closed.

Allowed persisted values:

- checkpoint/schema/policy identifiers;
- categorical states defined in this plan;
- booleans and bounded counts;
- monotonic durations;
- route labels such as `packaged-activation`, `base-protocol`, `uia-focus`, `documented-app-server-boundary`;
- generic error categories;
- relative evidence references.

Forbidden persisted values:

- username, SID, session token/number, PID, handle, AUMID/package family raw value, executable/install path, command line;
- protocol URL beyond the fixed label `base-protocol`;
- thread/task/project IDs or names;
- window captions, UIA names/IDs, prompts, task content, conversation content;
- screenshots, pixels, audio, clipboard, keystrokes;
- raw process/package/UIA/session dumps.

Raw handles needed for an in-memory trial must be discarded before serialization. Privacy scan the final object and staged JSON before atomic replacement. Use same-directory atomic writes and collision-safe owned staging; do not overwrite unknown sidecars.

## Required verification

### Stage A

- All authorized files exist and only authorized files were created.
- Both schemas parse and reject unknown/invalid fields.
- Official-interface assessment cites current official OpenAI documentation and separates App Server thread control from desktop activation.
- Candidate selection is deterministic and does not guess a URI route.
- Synthetic suite passes twice with complete cleanup.
- Approval packets are exact and Stage B/C artifacts do not yet exist.
- No Codex or Windows state was changed.

### Stage B

- Approval matches the executed route/actions.
- Ten consecutive already-open trials pass.
- Correct current-session instance is reused every time.
- No duplicate/ambiguous instance, close, task mutation, or Voice operation occurs.
- Focus behavior is reported separately from shell readiness.

### Stage C

- Separate approval matches the executed close/launch route.
- Ten consecutive cold launches pass from proved absent state.
- All launches reach `shell-ready` within timeout in the current unlocked session.
- Trials 1–9 close gracefully without force; trial 10 ends open/ready.
- Unsupported locked/sleeping states are refused by preflight and never induced.
- No task/thread/Voice operation occurs.

### Final consistency

- Trial JSON validates against the canonical schemas.
- Shared CP-004 results validate and pass privacy filtering.
- Matrix, summaries, worker report, and canonical evidence agree.
- No temp/staging files remain after successful runs.
- Public repository remains unchanged by the worker.

## Pass criteria

CP-011 may be accepted only when all of the following are true:

- one exact activation route is identified with provenance and approval history;
- ten consecutive already-open trials reuse the correct current-session app and reach `shell-ready`;
- ten consecutive cold trials launch the exact app from proved absent state and reach `shell-ready`;
- process start is never treated as readiness;
- foreground behavior and later-control implications are documented;
- locked/disconnected/sleeping/unknown sessions refuse before activation without wake/unlock attempts;
- cleanup never force-kills or closes a pre-existing unowned instance;
- no task or Voice content/action occurs;
- evidence is schema-valid, privacy-clean, internally consistent, and independently reproducible.

CP-011 completion makes its launch/session prerequisite available to CP-013, but CP-013 remains blocked until CP-012 also passes.

## Failure routes

- **Packaged activation unavailable/fails:** stop. Prepare a new exact base-protocol approval packet; do not invoke it automatically.
- **Base protocol opens an unexpected route/content:** stop, preserve categorical evidence, and reject the protocol candidate. Do not explore guessed variants.
- **App Server available but desktop UI unlinked:** document it as a thread/session boundary for CP-012/CP-013; do not count it as desktop launch.
- **Shell never becomes ready:** narrow supported launch conditions or find a stronger positive readiness signal before proceeding.
- **Foreground focus is denied:** record it and determine whether later UIA can operate without focus; do not send keys or use focus-stealing workarounds.
- **Duplicate/ambiguous app instance:** fail closed and do not interact with either instance.
- **Graceful close fails:** stop cold trials; do not force kill. Manual test setup may be proposed for renewed approval, but production launch proof remains separate from test cleanup.
- **Unexpected sign-in/update/error/task/Voice state:** stop for user review; do not click through.
- **Session ownership cannot be proved:** unsupported configuration; do not activate.
- **Privacy/schema/cleanup failure:** reject evidence and keep CP-011 incomplete.

## Worker handoff

Return a concise report containing:

1. Files created or changed.
2. Current official OpenAI documentation assessment and access date.
3. App Server availability/boundary conclusion without thread calls.
4. Candidate ranking and selected Stage B/C route.
5. Synthetic suite names, counts, two complete runs, exit codes, and cleanup state.
6. Exact Stage B and Stage C approval packets.
7. Confirmation that no live activation, focus, minimize, close, protocol invocation, App Server thread call, task action, Voice action, commit, or push occurred in Stage A.
8. Limitations, blockers, and any renewed approval required.

Do not mark CP-011 complete, start CP-012/CP-013, commit, push, or edit public status. Completion remains with Codex after Stage B and Stage C evidence is independently reviewed.
