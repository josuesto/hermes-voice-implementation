# CP-012 Implementation Plan — Recent-task enumeration and stable task identity

> **Mandatory workflow:** Codex plans and reviews; Grok 4.6 in Cursor implements the bounded checkpoint; Codex alone accepts and publishes completion. Private task metadata and machine evidence never enter this repository.

Checkpoint: **CP-012**  
Depends on: **CP-010 — Complete**  
Status: **Ready**

## Objective

Prove a deterministic, privacy-bounded way to obtain up to ten recent supported Codex tasks for the Hermes session picker. A stable task ID—not a title—must define identity. This checkpoint does not open, resume, create, rename, archive, delete, or inspect the turns of a task.

## Supported route

Use only the documented Codex App Server `thread/list` method over a worker-owned local stdio connection. Official documentation: <https://learn.chatgpt.com/docs/app-server>.

The live query is bounded to ten non-archived top-level interactive results, sorted by recency, with `useStateDbOnly=true`. No experimental capability, network listener, direct database/rollout-file read, UI Automation, keyboard, screenshot, or OCR fallback is allowed.

## Privacy boundary

The private adapter may transiently handle the stable ID and optional user-facing `name` needed for the product. It must immediately discard preview text, prompts, turns, responses, paths, Git metadata, and all unknown content-bearing fields.

Private evidence may contain only result counts, rank aliases, `name_present` and coarse length categories, allowlisted source/status categories, stability booleans, sanitized errors, durations, cleanup state, and a passing privacy-policy record. Raw IDs, names, previews, paths, exact timestamps, and content are forbidden from evidence and console output.

## Stages

### Stage A — implementation and synthetic proof

- Build a closed-schema read-only App Server client and synthetic harness in the private planning workspace.
- Permit only `initialize`, `initialized`, and `thread/list`.
- Require `-UserApproved` before any live child process can start.
- Test valid 0/1/10 results, bounds, malformed/error/timeout cases, duplicate or unstable IDs, null names, privacy rejection, forbidden-method refusal, and owned-child cleanup.
- Produce a separate Stage B approval packet and stop.

### Stage B — separately approved live proof

- Start three short-lived local App Server stdio children sequentially.
- Perform exactly one identical `thread/list` query per connection.
- Compare IDs, names, sources, and order only in memory with an ephemeral key.
- Persist one sanitized private report after schema and privacy validation.
- End only worker-owned child processes and leave every Codex task unchanged.

## Acceptance

CP-012 passes when three approved live calls return no more than ten uniquely identified supported tasks with stable IDs; optional names are handled without becoming identity or entering evidence; null-name tasks have a non-content fallback label contract; no task mutation/read/resume occurs; cleanup is owned and complete; and schema/privacy checks pass.

If the documented method is absent, IDs are unstable, privacy cannot be preserved, or cleanup fails, stop. Do not fall through to UI scraping or direct local-data inspection.
