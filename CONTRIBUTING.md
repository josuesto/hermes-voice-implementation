# Contributing

Hermes Voice Implementation is an active vertical-slice MVP with a working same-host Windows prototype, but no packaged release yet. The [MVP roadmap](docs/mvp-roadmap.md) is the current execution gate; the detailed checkpoint map remains the source for later compatibility, security, and release hardening.

## Checkpoint workflow

Prototype work is organized by the short milestones in [docs/mvp-roadmap.md](docs/mvp-roadmap.md). Release-hardening work uses the permanent checkpoints in [docs/checkpoint-map.md](docs/checkpoint-map.md). Each change should identify its milestone or checkpoint, stay within scope, and include proportionate tests and reproducible evidence.

For the creator's current workflow, Codex plans and reviews checkpoint work, while Grok 4.6 in Cursor is the designated implementation worker. That designation describes the maintainer's workflow rather than a restriction on community participation. External contributors may propose documentation, research, evidence, or later implementation changes through normal GitHub issues and pull requests.

## Accepted-checkpoint publication

Codex completes its independent review before any checkpoint is represented as accepted. After acceptance, Codex makes one public-safe commit and pushes it to `main`, then verifies the remote result. That commit contains only the accepted public outcome and sanitized status or evidence references. Private machine evidence, credentials, audio, transcripts, prompts, task content, personal paths, and other sensitive material remain outside Git. Rejected or incomplete work is not published or described as a completed checkpoint.

Before contributing:

1. Read the [plan](docs/plan.md) and active [MVP roadmap](docs/mvp-roadmap.md).
2. Identify the relevant milestone; use the [checkpoint map](docs/checkpoint-map.md) for release-hardening work.
3. Keep the proposal within the checkpoint's explicit scope; record architecture changes as ADRs when that stage is authorized.
4. Explain how the change was verified and include only sanitized, reproducible evidence.
5. Wait for the risk-based milestone or checkpoint review before describing work as accepted.

Do not create billable/provider resources or publish releases outside an authorized milestone. Do not commit personal machine inventory, credentials, tokens, provider/account data, IP or MAC addresses, Telegram details, Codex prompts or task content, logs containing sensitive data, transcripts, or audio.

Security-sensitive reports should follow [SECURITY.md](SECURITY.md), not a public issue.
