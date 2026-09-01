# CP-040 Implementation Plan — User-Owned Provider Requirements and Adapter Contract

> **Mandatory workflow:** Codex is the planner, technical reviewer, and checkpoint authority. Grok 4.6 in Cursor is the implementation worker. Grok performs only research and contract design in this checkpoint, does not mark completion, and does not commit or push. Codex independently verifies sources, consistency, and deterministic selection before publishing accepted public-safe documentation.

Worker: **Grok 4.6 in Cursor**  
Planner/reviewer: **Codex**  
Checkpoint: **CP-040**  
Depends on: **CP-003 and CP-004 — Complete**  
Scope: **Provider-neutral contract, current official-source comparison, and reference-candidate recommendation; no provider login or resources**

## Objective

Define a precise, testable provider-adapter contract that keeps the phone page/signaling route, direct ICE/STUN, and TURN relay as separate concerns. Compare credible user-owned infrastructure paths and select the reference candidate—or explicit composed reference path—that CP-041 through CP-046 should prove.

The contract must preserve the product decisions already frozen:

- no mandatory project-operated shared service;
- each user owns the meeting point/resources/account;
- no custom domain requirement;
- Hermes supplies the current usable link;
- Cloudflare is the intended first candidate, not a predetermined winner for every concern;
- Quick Tunnels are development-only unless authoritative production support says otherwise;
- direct media and relay fallback remain separate from page/signaling;
- billable operations require preview and explicit approval;
- provider choice is deterministic, not improvised by the language model.

CP-040 does not authenticate to Cloudflare or any provider, deploy a page, create a hostname, open a tunnel, mint credentials, start STUN/TURN, or incur cost. CP-041 through CP-043 own live proofs.

## Working locations

The execution workspace is maintainer-local, private, and ignored by Git. Its absolute path is intentionally unpublished. All `work/` paths below are relative to that private workspace and are not public-repository artifacts.

Create or edit only:

```text
work/feasibility/network/cp-040/
  README.md
  schema/
    provider-adapter-contract.schema.json
    provider-capability-record.schema.json
  reports/
    provider-adapter-contract.md
    provider-comparison-matrix.md
    reference-candidate-selection.md
    source-register.md
  scripts/
    Test-ProviderContract.ps1
  cp-040-worker-report.md
```

The shared harness may add one sanitized CP-040 result under `work/feasibility/network/results/`.

Public read-only sources:

- [`docs/plan.md`](../plan.md), [`docs/checkpoint-map.md`](../checkpoint-map.md), and [this CP-040 implementation plan](cp-040-provider-contract-implementation-plan.md);
- [`docs/security/threat-model-v0.md`](../security/threat-model-v0.md), [`docs/security/data-flow-v0.md`](../security/data-flow-v0.md), and [ADR 0001](../adr/0001-user-owned-infrastructure-no-mandatory-shared-service.md);
- current official provider product, API, pricing, quota, terms, hostname, WebSocket, STUN, TURN, credential, and cleanup documentation needed for each matrix claim.

Private read-only source, not included in Git:

- CP-004 harness and privacy documentation.

Do not edit the public repository during worker execution.

## Mandatory boundaries

- Do not sign into Cloudflare or any provider.
- Do not read browser sessions, cookies, API tokens, OAuth state, account IDs, zones, domains, billing details, or existing provider resources.
- Do not install or run `cloudflared`, Wrangler, Terraform, provider CLIs, Coturn, reverse proxies, or deployment tools.
- Do not create, modify, start, stop, or delete a tunnel, Worker, Pages project, Durable Object, hostname, DNS record, certificate, STUN/TURN allocation, server, firewall rule, or billable resource.
- Do not test a live URL, WebSocket, ICE, STUN, TURN, cellular route, or VPS.
- Do not infer features from product names or marketing summaries. Decisive claims need current primary official sources.
- Do not call an option free forever. Record current documented pricing/quota status with an `as of` date and a change-risk note.
- Do not copy provider docs wholesale. Summarize and cite.
- Do not put domains, account details, IPs, hostnames, tokens, or personal paths in evidence.
- Do not freeze an exact Cloudflare Workers/Tunnel/TURN architecture without CP-041–CP-043 evidence.
- Do not treat a page-loading tunnel as a TURN solution.
- Do not choose a project-operated relay/control plane as the default.
- Do not claim provider compatibility for a dedicated native phone app; the client is a normal supported mobile browser.

## Research method

Provider facts are time-sensitive. For every external claim:

- use the provider/project's official product/API/pricing/terms documentation;
- record direct URL, page title, publisher, and access date;
- distinguish documented fact, observed local fact, architectural inference, and unverified question;
- prefer at least two official pages when one claim spans product behavior and pricing/terms;
- note region/account/plan limitations;
- do not quote more than necessary;
- mark stale, ambiguous, or contradictory documentation `requires_live_validation`.

The worker may use web search only to locate primary official pages. The final matrix must cite primary sources, not search-result snippets or third-party blog posts. No authenticated dashboard browsing is authorized.

## Network-concern separation

The contract and matrix must model these independently:

### Concern A — page and signaling

- browser-reachable HTTPS page;
- trusted TLS without user certificate bypass;
- WebSocket or equivalent bidirectional signaling;
- provider-assigned hostname;
- custom domain optional/not required;
- hostname stability class across route restarts;
- companion outbound connection or bounded provider-side endpoint;
- start/stop/status/current-link operations;
- route inactive behavior;
- page asset serving/update model.

### Concern B — direct WebRTC discovery

- ICE signaling compatibility;
- STUN server/configuration source;
- UDP/TCP/TLS candidate implications;
- no use of STUN as user authentication;
- privacy-safe diagnostics that record candidate class, never addresses.

### Concern C — relay fallback

- TURN over required transports;
- browser compatibility;
- short-lived session-scoped credentials;
- credential mint/revoke/expiry mechanism;
- relay regions and cost/bandwidth model;
- DTLS-SRTP remains end-to-end between peers;
- no decoded audio requirement;
- forced-relay testability;
- self-hosted Coturn or provider relay composition when one provider does not supply TURN.

One adapter may satisfy all concerns, or a deterministic composed reference path may use separate user-owned components. The contract must expose that composition honestly.

## Provider adapter contract

### Identity and ownership

- adapter ID and semantic contract version;
- provider/component IDs;
- account/resource ownership model;
- supported deployment modes;
- credential classes required, without values;
- ownership validation operation;
- supported Windows/host/runtime prerequisites;
- custom-domain policy enum: `not_required`, `optional`, `required`;
- central-project dependency boolean, required to be false for the default path.

### Capability declaration

Each adapter declares `supported`, `unsupported`, `composed`, `unknown`, or `requires_live_validation` for:

- page assets;
- HTTPS hostname;
- WebSocket signaling;
- stable versus per-session assigned URL;
- outbound host channel;
- STUN;
- TURN UDP/TCP/TLS;
- short-lived TURN credential minting;
- health/status;
- start/stop;
- current link;
- usage/cost estimate;
- teardown/revocation;
- resource enumeration limited to project-created resources;
- development-only modes.

### Operations

Define request/result/error contracts for:

1. `describePrerequisites`
2. `previewSetup`
3. `authenticateOrValidateOwnership`
4. `provisionOrValidateRoute`
5. `startRoute`
6. `getCurrentLink`
7. `getSignalingConfiguration`
8. `getStunConfiguration`
9. `mintTurnCredentials`
10. `runHealthCheck`
11. `previewCostImpact`
12. `stopRoute`
13. `revokeSessionCredentials`
14. `previewCleanup`
15. `cleanupProjectResources`

Every mutating operation requires an explicit preview object and approval token/decision supplied outside the model prompt. The contract must distinguish read-only validation from billable or destructive actions.

### Lifecycle and idempotency

- setup state, configured state, inactive route, starting, ready, degraded, stopping, stopped, cleanup pending, failed;
- resource IDs represented as opaque protected handles, not logs;
- idempotency keys;
- timeout/retry classes;
- crash reconciliation;
- current-link refresh behavior;
- stable/dynamic hostname semantics;
- cleanup limited to resources created/tagged by this project;
- unrelated provider resources are never deleted.

### Errors

Use safe categories such as:

- `not_authenticated`
- `ownership_unverified`
- `capability_unsupported`
- `custom_domain_required`
- `hostname_unavailable`
- `tls_unready`
- `signaling_unavailable`
- `stun_unavailable`
- `turn_unavailable`
- `quota_exceeded`
- `billing_approval_required`
- `credential_expired`
- `provider_policy_changed`
- `cleanup_failed`
- `unknown`

No raw provider error body, account ID, domain, hostname, IP, token, or dashboard output enters public or shared evidence.

### Security and secret storage requirements

- provider credentials remain on the Windows companion in Windows Credential Manager or equivalent OS-protected storage;
- no token in Hermes prompts, skill files, logs, URL query strings, phone storage, or evidence;
- minimum scopes and rotation/revocation guidance;
- TLS for control/signaling;
- device/session authentication remains separate from provider URL access;
- URL knowledge is never authorization;
- short-lived TURN credentials and End Session invalidation;
- provider compromise residual-risk statement consistent with CP-003.

### Cost and approval model

Represent:

- resource creation cost class;
- fixed versus usage-based cost;
- signaling/request usage;
- relay bandwidth/minutes/egress;
- quotas/limits;
- trial/free allowance as time-sensitive informational data only;
- exact operations that may become billable;
- pre-action preview and explicit user approval;
- no blanket authorization to create billable resources.

## Candidate comparison set

Evaluate at least:

1. Cloudflare user-owned paths, separating development Quick Tunnel, provider-assigned page/signaling possibilities, outbound connectivity, STUN, and TURN/relay products or gaps.
2. User-owned VPS composed path: reverse proxy/TLS plus signaling plus Coturn.
3. At least one other credible browser-compatible user-owned/provider-account route that can supply a provider-assigned HTTPS address, while treating TURN separately if necessary.

Do not include an option merely to fill a row. If no third candidate satisfies ownership/browser/custom-domain requirements, record why it was screened out.

The matrix must include:

- concern coverage A/B/C;
- provider-assigned hostname and stability class;
- custom-domain requirement;
- automatic setup feasibility;
- user account/server ownership;
- Windows companion outbound-connectivity model;
- browser WebSocket/WebRTC compatibility;
- STUN/TURN support and credential model;
- region/network limitations;
- setup/admin/runtime dependencies;
- resource cleanup model;
- licensing/terms constraints;
- current cost/quota classes;
- source quality/date;
- live validations owned by CP-041/042/043;
- rejection reasons.

## Deterministic selection policy

### Mandatory gates

A reference candidate/composition must:

- remain entirely user-owned;
- require no project-operated shared backend;
- provide a browser-trusted HTTPS address without requiring purchase of a custom domain;
- support WebSocket/equivalent signaling;
- permit automated or guided reproducible setup;
- expose the current link to Hermes;
- support or compose with STUN and short-lived TURN fallback;
- have a scoped cleanup/revocation story;
- disclose all possible billable operations before action;
- support the target normal mobile-browser flow;
- have no known terms conflict with the open-source integration.

### Ranking after gates

Rank passing paths in this order:

1. clearest user ownership and least project custody;
2. reproducible no-custom-domain setup;
3. strongest browser/TURN compatibility;
4. least persistent host/provider complexity;
5. clearest cost preview and cleanup APIs;
6. best official documentation and maintainability;
7. lowest expected user burden.

No hidden weights and no “the agent decides.” The selection report must show each gate and tie-break.

## Schemas and test script

### `provider-adapter-contract.schema.json`

Closed JSON Schema for the stable contract shapes above. Bound lengths/arrays, disallow unknown fields, and forbid secrets/addresses/content. Model capability composition and mutating-operation approval explicitly.

### `provider-capability-record.schema.json`

Closed schema for one researched candidate with:

- safe candidate ID;
- concern capabilities/status;
- ownership/custom-domain/hostname classes;
- setup/runtime/cleanup/cost classes;
- source references as official HTTPS URLs only;
- access dates;
- live-validation owners;
- decision/rejection state;
- no account/provider resource data.

### `Test-ProviderContract.ps1`

- PowerShell 5.1 compatible; no network calls.
- Parse both schemas and validate representative synthetic candidates/compositions.
- Reject unknown capabilities, ambiguous ownership, mandatory project backend, required custom domain for the default path, no TURN story, unapproved billable mutations, unsafe cleanup, secrets, IPs, account IDs, raw provider errors, and non-official source URL shapes.
- Prove deterministic selection produces the same winner/order regardless of input row order.
- Prove a Quick Tunnel-only candidate cannot qualify as production merely because it supplies a page URL.
- Prove a page/signaling-only candidate cannot claim relay coverage.
- Prove a composed VPS/Coturn or provider-plus-TURN path can represent split ownership honestly.
- Use `.selftest-temp`, run twice, cleanup in `finally`, and emit totals/exit code.

## Execution sequence

1. Extract frozen requirements from CP-003/ADR 0001 and the canonical plan.
2. Implement schemas and deterministic selection tests first.
3. Run offline self-tests twice.
4. Research current official documentation without authentication.
5. Fill the source register and capability records, marking unknowns honestly.
6. Produce the comparison matrix.
7. Run the deterministic gates/ranking.
8. Write the reference selection with alternatives and CP-041/042/043 live-test obligations.
9. Run privacy/publication scans.
10. Record one sanitized CP-040 harness result.
11. Write the worker report and stop.

## Acceptance criteria

Codex may accept CP-040 only when:

- contract concerns A/B/C remain distinct;
- every operation, state, approval, error, cleanup, secret, and cost responsibility is explicit;
- one candidate/composition plausibly supplies a provider-assigned browser URL plus relay fallback in user-owned infrastructure without a mandatory custom domain;
- Cloudflare is evaluated as the intended first candidate without freezing an untested mechanism;
- Quick Tunnels are development-only;
- provider selection is deterministic and reproducible;
- all decisive current facts cite official primary sources and unknowns are assigned to live checkpoints;
- no provider login/resource/network test occurred;
- schemas/tests pass twice and clean temporary state;
- evidence contains no accounts, domains, hostnames, IPs, credentials, private paths, or raw provider output;
- no unsupported compatibility, stability, pricing, or production claim is made.

## Failure route

If no no-custom-domain candidate/composition passes the mandatory gates, recommend a user-owned VPS reference path or revise the stable-URL requirement through a new ADR. Do not weaken user ownership, add a mandatory project service, or pretend a page tunnel supplies TURN.

## Worker handoff

Report:

1. Files created.
2. Official sources and access dates.
3. Contract capability/operation summary.
4. Candidate gates, ranking, and recommendation.
5. Unknowns assigned to CP-041/042/043.
6. Offline self-test totals and deterministic-order proof.
7. Privacy/state-change verification.
8. Blockers or ADR conflict.

Do not mark CP-040 complete, commit, push, authenticate, create resources, or start CP-041. Completion is left to Codex.
