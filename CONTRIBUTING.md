# Contributing

Hermes Voice Implementation is currently a documentation-first feasibility project. There is no working release or production code. CP-002 is Complete, CP-003 and CP-004 are Ready, and production implementation remains blocked until the Phase Zero gate passes.

## Checkpoint workflow

Work is organized by the permanent checkpoints in [docs/checkpoint-map.md](docs/checkpoint-map.md). Each change must identify its checkpoint, stay within that checkpoint's scope, and provide the required tests and reproducible evidence. A checkpoint is not passed because code or a worker report exists; its stated evidence and acceptance criteria must pass independent review.

For the creator's current workflow, Codex plans and reviews checkpoint work, while Grok 4.6 in Cursor is the designated implementation worker. That designation describes the maintainer's workflow rather than a restriction on community participation. External contributors may propose documentation, research, evidence, or later implementation changes through normal GitHub issues and pull requests.

## Accepted-checkpoint publication

Codex completes its independent review before any checkpoint is represented as accepted. After acceptance, Codex makes one public-safe commit and pushes it to `main`, then verifies the remote result. That commit contains only the accepted public outcome and sanitized status or evidence references. Private machine evidence, credentials, audio, transcripts, prompts, task content, personal paths, and other sensitive material remain outside Git. Rejected or incomplete work is not published or described as a completed checkpoint.

Before contributing:

1. Read the [plan](docs/plan.md) and [checkpoint map](docs/checkpoint-map.md).
2. Identify the relevant checkpoint and confirm its dependencies are complete.
3. Keep the proposal within the checkpoint's explicit scope; record architecture changes as ADRs when that stage is authorized.
4. Explain how the change was verified and include only sanitized, reproducible evidence.
5. Wait for checkpoint review. No contribution, including a maintainer change, passes a checkpoint without its required evidence and review.

Do not add product scaffolding, dependencies, CI, releases, or provider resources while CP-100 remains blocked. Do not commit personal machine inventory, credentials, tokens, provider/account data, IP or MAC addresses, Telegram details, Codex prompts or task content, logs containing sensitive data, transcripts, or audio.

Security-sensitive reports should follow [SECURITY.md](SECURITY.md), not a public issue.
