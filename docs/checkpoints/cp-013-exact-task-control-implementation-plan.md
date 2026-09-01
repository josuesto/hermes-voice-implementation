# CP-013 — Exact Create/Open/Verify Task Control Implementation Plan

Status: ready for Stage A only
Checkpoint owner: Codex
Implementation worker: Grok 4.6 in Cursor
Review policy: prototype-fast

## 1. Outcome

Prove that the adapter can select one exact existing Codex task or create one exact empty task, correlate that identity with the desktop task that will later receive Voice, and fail closed before Voice whenever identity is ambiguous.

CP-012 proved stable, privacy-reduced enumeration. CP-013 must prove act-and-verify. A successful App Server response alone is not proof that the Codex desktop UI opened the same task.

## 2. Official interface basis

Use only the stable methods documented by the [Codex App Server documentation](https://learn.chatgpt.com/docs/app-server) and confirmed by schemas generated from the installed CLI version:

- `initialize` followed by `initialized` once per connection;
- `thread/list` for the fresh selection set;
- `thread/resume` for an existing task;
- `thread/start` for a new empty task;
- `thread/read` with `includeTurns=false` for identity/status verification without loading turns;
- `thread/loaded/list` for loaded-identity verification;
- `thread/name/set` only for a worker-created disposable task;
- `thread/unsubscribe` to release the worker's subscription;
- `thread/archive` only as reversible cleanup of a task created by the current trial.

Do not enable `experimentalApi`. The installed CLI's generated schema is authoritative for exact parameter shapes. If a required stable method is absent or incompatible, stop with `supported_method_unavailable`.

## 3. Non-goals and hard prohibitions

- Do not call `turn/start`, `turn/steer`, `turn/interrupt`, `thread/delete`, `thread/fork`, `thread/inject_items`, shell-command methods, or any Voice method.
- Do not read turns, previews, prompts, responses, files, rollout JSONL, or databases directly.
- Do not guess a `codex://` task URL or undocumented method.
- Do not select by row position or visible title alone.
- Do not click coordinates, send broad keyboard shortcuts, or use OCR.
- Do not close Codex, archive an existing user task, or delete any task.
- Do not persist raw task IDs, names, paths, exact timestamps, instruction-source paths, or task content.
- Do not start Stage B or C without the separate user approval described below.

## 4. Authorized private files

Create only:

```text
work/feasibility/codex-control/cp-013/
  README.md
  schema/task-control-observation.schema.json
  scripts/Invoke-Cp013TaskControl.ps1
  scripts/Test-Cp013TaskControlHarness.ps1
  reports/stage-b-resume-approval-packet.md
  reports/stage-c-create-approval-packet.md
  cp-013-worker-report.md
```

Live result files are authorized only after their stage is approved:

```text
  reports/existing-task-trials.json
  reports/new-task-trials.json
```

All files remain private and Gitignored. Do not edit public documentation, checkpoint status, other feasibility tracks, or CP-014.

## 5. Stage A — non-mutating preparation

Stage A may run now. It must not start a live App Server child or touch Codex task state.

### 5.1 Installed-interface capture

- Record `codex --version` as a bounded version string.
- Run `codex app-server generate-json-schema` into a disposable directory inside the authorized CP-013 tree.
- Extract only method presence and required parameter/result field names for the allowed methods.
- Delete generated raw schemas after deriving the bounded allowlist; do not copy unrelated schema content into evidence.
- If schema generation is unavailable, record the dependency failure and stop before any live stage.

### 5.2 Script contract

`Invoke-Cp013TaskControl.ps1` must:

- default to synthetic mode;
- require `-UserApproved` plus a stage-specific authorization object for live mode;
- accept only exact booleans, enums, bounded integers, and safe relative paths;
- refuse unsupported methods before process start;
- start only worker-owned `codex app-server` stdio children;
- keep raw IDs and names in memory only;
- reduce live evidence before serialization;
- validate the closed Draft 2020-12 schema and shared privacy filter before finalizing;
- clean up only the subscription/child/task created by the current trial;
- never kill, close, archive, rename, or otherwise mutate an unowned object.

### 5.3 Synthetic harness

The harness covers:

- exact type and enum validation for all authorization fields;
- refusal without approval and refusal of every forbidden method;
- three-call resume identity match/mismatch fixtures;
- stale enumeration, missing target, duplicate-title ambiguity, renamed target, and reordered list fixtures;
- `thread.resume.id == selected.id`, `thread.read.id == selected.id`, and loaded-list membership checks;
- proof that logical resume without desktop correlation cannot pass;
- create response/read/list/desktop-correlation agreement;
- owned-task rename/archive cleanup and refusal to archive an unowned ID;
- timeout, malformed JSONL, App Server error, child exit, and cleanup failure;
- privacy rejection for IDs, names, paths, prompts, turns, previews, timestamps, credentials, and content-like fields;
- no temp/final evidence after rejected cases.

Run the synthetic suite once. Additional reruns are required only after a failing test or implementation change.

### 5.4 Stage A stopping point

Write both approval packets and stop. Do not run a live App Server process, focus Codex, inspect live UI Automation, resume a task, or create a task.

## 6. Stage B — existing-task resume and desktop correlation

Stage B requires Codex acceptance of Stage A and a fresh explicit user approval naming the intended existing task privately. The packet must state that the operation loads/subscribes to the task but starts no turn and changes no task content.

Run three trials against the same user-approved existing task:

1. Start one owned App Server child and initialize it.
2. Run the CP-012 packed `thread/list` query and resolve the approved task to a stable raw ID in memory. If the private title/context is ambiguous, stop before resume.
3. Call `thread/resume` with that exact ID.
4. Verify the returned `thread.id` equals the selected ID.
5. Call `thread/read` with `includeTurns=false`; verify the same ID and an allowlisted status.
6. Call `thread/loaded/list`; verify the exact ID is loaded.
7. Observe the already-running desktop Codex window through privacy-reduced semantic UI Automation only. Record whether the desktop exposes enough non-content identity to prove that its active task is the selected task. Persist only `desktop_identity_verified=true|false` and a reason enum.
8. Call `thread/unsubscribe` for the selected task and end only the owned child.

Stage B passes only if all three trials agree on the stable identity and independently prove the same desktop task. If App Server resume is logical/headless only, or the desktop exposes no independent identity signal, stop CP-013 with `desktop_correlation_unproven`. Do not invent a deep link or fall through to clicking.

## 7. Stage C — new empty task creation and reversible cleanup

Stage C is separately approval-gated and may run only after Stage B passes. The packet must state that three empty tasks will be created, given unique non-sensitive test names, verified, and archived. No turn or prompt will be created.

For each of three trials:

1. Start and initialize one owned App Server child.
2. Call `thread/start` using only installed-schema-supported stable fields and `serviceName=hermes_voice_cp013`.
3. Capture the returned ID in memory and prove it did not exist in the pre-trial list.
4. Set a unique bounded name such as `Hermes Voice CP-013 test <random-safe-suffix>` using `thread/name/set`.
5. Verify the same ID through `thread/read(includeTurns=false)`, `thread/list`, and `thread/loaded/list`.
6. Prove the desktop active task correlates to that exact created identity using the Stage B accepted signal.
7. Call `thread/unsubscribe`.
8. Archive only the exact task ID created by the current trial; verify it is absent from the non-archived list and present in the archived list.
9. End only the owned child.

If cleanup cannot prove ownership, preserve the task and report `cleanup_failed`; never archive or delete a different task. `thread/delete` remains forbidden.

## 8. Sanitized evidence contract

Each report contains only:

- schema/checkpoint/script versions and coarse timestamp date;
- stage, route, CLI version, trial count, and final/failure status;
- per-trial alias, action enum, result enum, duration buckets, identity-agreement booleans, desktop-correlation boolean/reason enum, cleanup ownership/state, and error category;
- aggregate zero-wrong-task, zero-content-mutation, external-state-changed, and privacy-review booleans.

Raw IDs, names, hashes/digests, paths, exact timestamps, UI strings, task contents, responses, and instruction-source values are forbidden. The HMAC/alias key is per-run and discarded.

## 9. Acceptance criteria

CP-013 is complete only when:

1. Stage A is accepted under prototype-fast review.
2. Stage B has three approved final trials with exact resume/read/loaded identity agreement and independent desktop-task correlation.
3. Stage C has three approved final trials with exact create/read/list/loaded/desktop identity agreement.
4. Every created test task is either archived by proven ownership or explicitly reported as preserved after cleanup failure; nothing is deleted.
5. No wrong task, turn, prompt, response, Voice action, or unapproved mutation occurs.
6. Both reports pass the closed schema and `privacy-policy-1.0.0` with zero findings.
7. No unowned process/window/task is closed, killed, renamed, archived, or otherwise modified.

On success, CP-013 unlocks CP-014. On failure, preserve the browser/audio/network tracks, keep Voice blocked, and write a narrower route-specific follow-up instead of weakening identity verification.

## 10. Worker handoff for this pass

Implement **Stage A only**. Return:

- files created;
- installed method/schema-presence summary;
- synthetic test count and result;
- exact live refusal behavior;
- privacy and cleanup checks;
- the two approval-packet paths;
- blockers and limitations.

Do not run Stage B or C, mark CP-013 complete, edit public docs, commit, push, or begin CP-014.
