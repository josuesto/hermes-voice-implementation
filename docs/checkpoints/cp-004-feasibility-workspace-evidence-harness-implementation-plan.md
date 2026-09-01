# CP-004 Implementation Plan — Feasibility Workspace and Evidence Harness

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-004**  
Scope: Disposable local feasibility harness only; no Codex/audio/browser/provider spike implementation

## Objective

Create a reproducible, privacy-preserving local workspace that the four Phase Zero tracks can use to record sanitized pass, fail, blocked, error, duration, dependency, and cleanup outcomes. Prove the harness itself can generate dated results, reject unsafe evidence, record forced failures accurately, and clean its temporary state. Do not investigate Codex control, modify audio, serve a phone page, or connect to Cloudflare during this checkpoint.

## Working location

The execution workspace is maintainer-local, private, and ignored by Git. Its absolute path is intentionally unpublished. All `work/` paths below are relative to that private execution workspace.

Read:

- [`docs/plan.md`](../plan.md)
- [`docs/checkpoint-map.md`](../checkpoint-map.md)
- CP-002 inventory: private maintainer evidence, not included in Git.

The public repository intentionally ignores `work/`. This checkpoint's raw/local harness evidence remains private until Codex later decides which generic harness files are safe and useful to publish. Do not edit or commit the public repository during worker implementation.

## Mandatory boundaries

- Create or edit only the files listed below under `work\feasibility`.
- Do not launch, close, automate, or inspect Codex, Hermes, Telegram, browsers, audio applications, or Cloudflare/provider interfaces.
- Do not install packages, dependencies, drivers, browsers, services, or command-line tools.
- Do not request administrator privileges.
- Do not change registry, audio, power, firewall, VPN, network, scheduled-task, credential, provider, or application state.
- Do not capture microphone/system/Codex audio and do not create media recordings.
- Do not query IP/MAC addresses or provider credentials.
- Do not read prompts, task titles/content, transcripts, bot configuration, tokens, cookies, browser storage, or credential stores.
- Do not scaffold production directories such as `companion`, `plugin`, `web`, `providers`, or CI.
- Use only standard PowerShell/.NET capabilities already present. No new dependency is authorized.
- Do not commit or push. Codex will review and publish only an accepted public-safe checkpoint outcome.
- Do not mark CP-004 complete or start CP-010, CP-020, CP-030, or CP-040.

## Files and directories to create

```text
work/feasibility/
  README.md
  schema/
    feasibility-result.schema.json
  scripts/
    New-FeasibilityResult.ps1
    Test-EvidencePrivacy.ps1
    Invoke-FeasibilityHarnessSelfTest.ps1
  examples/
    sanitized-pass.json
    sanitized-failure.json
  codex-control/
    README.md
    results/
  audio/
    README.md
    results/
  phone/
    README.md
    results/
  network/
    README.md
    results/
  cp-004-worker-report.md
```

Empty `results` directories do not need placeholder files if the self-test produces and then removes temporary results. Track READMEs must make the intended path clear.

Do not create any additional persistent file unless required for a test. Self-test temporary files must live under `work\feasibility\.selftest-temp` and must be removed in a `finally` block.

## Common result schema

`feasibility-result.schema.json` must be valid JSON Schema and define at least:

- `schema_version` — start at `1.0.0`.
- `checkpoint` — stable checkpoint ID such as `CP-010`.
- `track` — enum: `codex-control`, `audio`, `phone`, `network`, `harness`.
- `test_id` — safe slug, not a task title or personal identifier.
- `timestamp_utc` — ISO 8601 UTC.
- `action` — concise predetermined operation label, not raw commands or user content.
- `expected_state` — sanitized state description.
- `observed_state` — sanitized state description.
- `duration_ms` — non-negative integer.
- `result` — enum: `pass`, `fail`, `blocked`, `error`.
- `error_category` — null or a safe enum/string category such as `dependency_missing`, `permission_denied`, `timeout`, `unexpected_state`, `cleanup_failed`, `privacy_rejected`, `unsupported`, `unknown`.
- `cleanup_state` — enum: `not_required`, `completed`, `failed`, `unknown`.
- `dependency_versions` — object of safe product/tool names to version strings; no paths or command output.
- `measurements` — optional object limited to numeric/boolean/safe-enum values.
- `evidence_refs` — optional repository/workspace-relative paths only; reject absolute paths and traversal.
- `notes` — optional short sanitized operational note.
- `privacy_review` — object stating whether the content filter passed and which policy version was used.

Disallow unknown top-level fields so later spikes do not smuggle raw payloads into evidence. Define maximum reasonable string lengths. Explicitly forbid content-bearing fields such as `prompt`, `task_content`, `transcript`, `model_response`, `audio`, `sdp`, `ice_candidates`, `raw_output`, or `command_line`.

## Script 1 — `New-FeasibilityResult.ps1`

Requirements:

- Accept typed parameters for every required schema field.
- Validate checkpoint format, track enum, result enum, cleanup enum, non-negative duration, safe test/action identifiers, safe error category, and relative evidence references.
- Build the object in memory.
- Serialize deterministic UTF-8 JSON.
- Run `Test-EvidencePrivacy.ps1` against the in-memory/temporary JSON before finalizing.
- Write atomically: create a temporary file in the destination directory, validate, then rename to a timestamped final filename.
- Default destination: `work\feasibility\<track>\results`.
- Filename: `<UTC basic timestamp>-<checkpoint-lower>-<test-id>.json` with collision-safe suffix if needed.
- Never overwrite an existing result.
- Return a small object containing final relative path, result, and privacy-filter outcome.
- On failure, remove its temporary file and leave any existing result unchanged.
- Provide comment-based help and examples containing no real identifiers or secrets.

The script must not run the action being measured. It records a caller-supplied sanitized summary only.

## Script 2 — `Test-EvidencePrivacy.ps1`

Requirements:

- Accept either a file path under the feasibility workspace or an in-memory string/object.
- Return a structured result with `Passed`, rule IDs, and safe messages; exit nonzero when used as a command and evidence is rejected.
- Never echo the matched secret/content value. Report rule name, filename, and line/property location only when safe.
- Reject at least:
  - Credential assignments/labels with values: API keys, access/refresh tokens, bearer authorization, passwords, cookies, bot tokens, client secrets, private keys.
  - Common token shapes for GitHub/OpenAI/JWT/bearer-style values.
  - Private-key blocks.
  - MAC, IPv4, and IPv6 address shapes. A later checkpoint may add an allowlisted version-field mechanism; this harness should default to fail closed.
  - Absolute Windows user paths, UNC paths, `file://` URLs, and path traversal in evidence references.
  - Email addresses and phone-number-like values.
  - Forbidden content field names: prompt, transcript, task/model content, response text, raw output, command line, SDP, ICE candidate payloads.
  - Audio/recording/packet-capture extensions or files: `.wav`, `.mp3`, `.m4a`, `.ogg`, `.webm`, `.flac`, `.pcap`, `.pcapng`.
  - Files larger than a conservative configured evidence-size limit.
- Allow harmless result enums, timings, checkpoint IDs, version strings, safe error categories, and relative evidence paths.
- Make rules versioned and documented in the README.
- Avoid recursively scanning the private CP-002 inventory when the worker runs the CP-004 self-test; scope checks to `work\feasibility`.

The filter is a guardrail, not proof that arbitrary prose contains no private content. The README must require human review and content allowlisting.

## Script 3 — `Invoke-FeasibilityHarnessSelfTest.ps1`

Requirements:

- Run without administrator privileges or external services.
- Use `try/finally` to delete `.selftest-temp` even when a test fails.
- Validate the schema JSON parses.
- Generate and parse one passing harness result.
- Generate and parse one forced-failure result with `result=fail`, a named error category, and `cleanup_state=completed`.
- Generate one forced cleanup-failure result with `cleanup_state=failed` and confirm it remains distinguishable from action failure.
- Test invalid enum, negative duration, unsafe test ID, absolute evidence path, and overwrite/collision behavior.
- Test the privacy filter's rejection behavior using transient generated strings for credential labels, address shapes, forbidden content fields, and disallowed media extensions. Do not persist secret-like fixtures after the test.
- Confirm rejected evidence never reaches a final `results` directory.
- Confirm each of the four track directories can receive a safe result through `New-FeasibilityResult.ps1`; create these in `.selftest-temp` or remove them after validation.
- Output a concise test summary with total, passed, failed, cleanup result, and exit code.
- Exit nonzero if any assertion fails.

Do not use Pester unless it is already an explicit standard dependency—which it is not for this checkpoint. Implement a small self-contained assertion helper.

## Sanitized examples

`sanitized-pass.json` and `sanitized-failure.json` must conform to the schema and pass the privacy filter.

The failure example must demonstrate:

- `result: fail`
- a safe `error_category`
- `cleanup_state: completed`
- no raw exception, stack trace, command, path, user content, IP, or secret

These are documentation examples, not claims that a real Codex/audio/phone/network test occurred.

## Root README

`work\feasibility\README.md` must explain:

- This is disposable Phase Zero infrastructure, not production code.
- The four tracks and their owning checkpoint ranges.
- The schema and script purposes.
- How to record results without raw output/content.
- The privacy rule version and fail-closed behavior.
- Evidence allowlist/denylist.
- Human review requirement.
- How to run the self-test.
- How later workers should create a result and attach only safe relative evidence.
- Cleanup expectations and the difference between action result and cleanup state.
- Prohibition on audio recordings, transcripts, prompts, model responses, task content, SDP/ICE payloads, IP/MAC addresses, credentials, absolute personal paths, and raw command output.
- No feasibility conclusion is accepted merely because the harness produced a file; Codex reviews each later checkpoint's real evidence.

## Track READMEs

Each track README must contain:

- Scope and owning checkpoint range.
- What kinds of sanitized measurements/results belong there.
- Explicit forbidden evidence.
- Expected cleanup responsibilities.
- A sample invocation using only fake/safe state labels.
- Statement that the directory currently contains no technical conclusion.

Track ownership:

- `codex-control`: CP-010 through CP-016.
- `audio`: CP-020 through CP-026.
- `phone`: CP-030 through CP-035.
- `network`: CP-040 through CP-046.

## Worker report

`cp-004-worker-report.md` must include:

- Files created.
- Design summary of schema, generator, filter, and self-test.
- Exact verification commands run.
- Self-test totals and outcomes.
- Forced-failure and cleanup-failure proof.
- Privacy rejection proof without echoing rejected values.
- Confirmation that `.selftest-temp` and other temporary files were removed.
- Confirmation that no external/system/application/provider state changed.
- Known limitations of regex/field-name filtering.
- Explicit statement that CP-004 completion is left to Codex.

## Verification required before handoff

Run only local file-content/script tests:

1. Parse `feasibility-result.schema.json`, `sanitized-pass.json`, and `sanitized-failure.json` with `ConvertFrom-Json`.
2. Run `Invoke-FeasibilityHarnessSelfTest.ps1` in a clean state at least twice to prove repeatability and cleanup.
3. Confirm the examples pass `Test-EvidencePrivacy.ps1`.
4. Confirm transient unsafe evidence is rejected and no value is echoed.
5. Confirm `.selftest-temp` is absent afterward.
6. Confirm the four real `results` directories contain no test artifacts after self-test.
7. Confirm every persistent file is under `work\feasibility` and matches the authorized tree.
8. Scan the persistent CP-004 tree for credentials, token shapes, IP/MAC addresses, personal paths, phone/email values, forbidden content fields, and media/packet-capture files.
9. Confirm no production repository file changed.

## Acceptance criteria

Codex may accept CP-004 only if:

- Each of the four tracks can produce a sanitized, dated schema-valid result.
- Forced action failure and forced cleanup failure are recorded distinctly and accurately.
- Unsafe evidence is rejected before finalization, with no rejected value echoed.
- Atomic write/collision behavior prevents overwrite or partial final files.
- Self-test is repeatable, produces an unambiguous exit code, and removes temporary state even on failure.
- Persistent examples conform to the schema and privacy policy.
- The workspace contains no actual audio, transcript, prompt/task content, raw command output, credential, address, personal path, or provider data.
- Nothing is packaged or represented as production code and no real feasibility conclusion is claimed.

## Worker handoff format

Report:

1. Authorized files created.
2. Harness/schema/filter behavior.
3. Self-test totals and repeatability.
4. Forced-failure/cleanup/privacy-rejection evidence.
5. Limitations or blockers.

Do not claim CP-004 is complete, commit, push, or begin any technical spike. Codex will independently review, rerun the self-test/privacy checks, request rework if needed, then update status and publish the accepted checkpoint commit.
