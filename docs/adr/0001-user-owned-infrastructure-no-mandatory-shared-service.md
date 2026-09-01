# ADR 0001: User-owned infrastructure with no mandatory project-operated shared service

Status: **Accepted as architecture baseline; provider mechanism still subject to Phase Zero.**
Date: 2026-09-01
Checkpoint: CP-003
Related: [threat model v0](../security/threat-model-v0.md), [data-flow v0](../security/data-flow-v0.md), [product plan](../plan.md), [checkpoint map](../checkpoint-map.md)

## Context

Hermes Voice Implementation needs a phone-reachable HTTPS page, signaling, optional STUN, and a TURN relay fallback so a paired browser can talk to a Windows companion. Those network objects could live in a project-operated multi-tenant service, in each user's account, or only on a LAN.

The product contract already forbids a central hosted control plane. Users must own the meeting point. A custom domain is not required. Hermes sends the current usable page link after Codex Voice is verified ready.

Cloudflare is the intended first candidate provider. A provider-assigned HTTPS hostname is acceptable. That does **not** freeze an exact Workers, Tunnel, or TURN architecture. Those mechanisms remain **to be validated** in CP-040 through CP-046. Cloudflare Quick Tunnels (`trycloudflare.com` style random URLs) are **development-only**, not the production decision.

## Decision

The project will not operate a mandatory shared signaling service, media relay, or control plane.

Each user supplies and controls provider resources in their own account. Version one will implement and test one reference provider adapter well. Cloudflare is the intended first candidate. Additional adapters may follow after their own security and compatibility evidence.

The companion remains the local authority for session activation. Provider resources are a meeting point, not an identity provider and not a place to store OpenAI, Telegram, or device private keys.

## Decision drivers

- Keep audio, Codex session, and owner commands out of a project-operated backend.
- Avoid a central cost, outage, and data-retention surface for all users.
- Match the open-source, self-hosted Hermes audience.
- Allow a provider-assigned hostname so users are not forced to buy a domain.
- Keep billing visible: every potentially billable operation needs preview and explicit approval.
- Preserve a later user-owned VPS/Coturn path without making it the only version-one route.

## Consequences

### Positive

- The project does not become a custodian of user media or account credentials.
- Users can revoke provider resources without waiting on a vendor operated by this project.
- Failure domains stay in the user's account and Windows session.

### Negative / accepted costs

- Setup requires a user-owned provider account and explicit approvals.
- Availability, quotas, and provider policy changes become the user's operational problem.
- The first adapter may not fit every network; TURN still has to be proven separately from a page tunnel.
- Documentation and setup UX must explain ownership, cost triggers, and cleanup.

## Alternatives considered

### Project-operated shared signaling/relay service

Rejected as the mandatory path. It would contradict the personal, user-owned design, create a central data/cost burden, and make the URL-plus-project-backend a high-value target.

### Mandatory custom domain or named tunnel

Rejected. A custom domain is not required. A Cloudflare or other provider-assigned HTTPS hostname is acceptable. Hermes supplies the current link.

### Local-LAN-only product

Rejected as the only product. LAN proof is required in earlier gates, but the original remote-from-cellular goal needs a user-owned internet meeting point.

### User-owned generic VPS as the only path

Deferred as a later/self-hosted option, not the sole version-one requirement. A small reverse-proxy plus Coturn reference may be documented later. It remains in the user's infrastructure.

## Security and privacy consequences

- Provider compromise can affect hostname, signaling availability, and TURN ciphertext relay. It must not yield OpenAI credentials or decoded audio if DTLS-SRTP and secret-boundary rules hold.
- URL leakage remains expected; pairing and session authorization are the access control.
- Short-lived TURN credentials and End Session invalidation limit relay abuse.
- No project-operated service means no project-side user database of devices or call metadata.

## Operational and cost consequences

- Users pay their provider, not a mandatory project fee for relay.
- Billable operations (hostname, TURN minutes, Workers invocations, or equivalent) **must** be previewed and approved at the time they are performed.
- Uninstall **must** offer cleanup of project-created provider resources without deleting unrelated account objects.

## Revisit triggers

- Phase Zero cannot prove a reproducible user-owned HTTPS plus TURN path on the intended first provider.
- The intended first provider forbids the required browser flows or forces a project-operated dependency.
- Legal or licensing constraints prevent distributing a provider adapter honestly.
- Evidence shows a LAN-only product is the only safe remaining scope; that would require an explicit product-boundary ADR.

## Related checkpoints

- CP-040 through CP-046: provider contract, route proof, STUN, TURN, pairing, roaming, qualification.
- CP-120 through CP-125: production provider path.
- CP-132: setup approvals and cost visibility.
- CP-150: adversarial tests including stolen URL and provider-compromise assumptions.
- CP-154: dependency, license, and supply-chain review.
