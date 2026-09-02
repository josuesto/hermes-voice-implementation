# ADR 0003: Vertical-slice MVP execution

- Status: Accepted
- Date: 2026-09-01

## Context

The original feasibility program applied release-grade evidence, schema, and adversarial-review requirements before the central audio path had been demonstrated. CP-013 alone accumulated extensive harness and review work while Codex Voice audio routing remained untested.

## Decision

The project will execute the first working prototype through the milestone sequence in [`docs/mvp-roadmap.md`](../mvp-roadmap.md). The legacy checkpoint map remains reference material for later hardening, but Gate F0 and exact existing-task resume no longer block prototype code.

The MVP starts a fresh Codex task, permits temporary manual setup or UI steps, and prioritizes a complete phone-to-Codex Voice audio loop. Reviews are short and risk-based. Credentials, destructive task operations, unauthorized system changes, recordings, and sensitive public evidence remain prohibited.

## Consequences

- Product code may begin before every legacy feasibility checkpoint is complete.
- Existing-task resume, broad compatibility, full provider abstraction, installer polish, and exhaustive adversarial testing are deferred.
- Some prototype code may be replaced after the end-to-end path is proven.
- Progress is measured by working calls, not by the number of evidence artifacts.
