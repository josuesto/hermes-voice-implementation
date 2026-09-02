"""Register same-host Codex Voice tools with the current Hermes plugin API."""

from __future__ import annotations

from pathlib import Path

from .tools import (
    START_SCHEMA,
    STATUS_SCHEMA,
    STOP_SCHEMA,
    check_windows,
    handle_codex_voice_start,
    handle_codex_voice_status,
    handle_codex_voice_stop,
)


def register(ctx) -> None:
    if not check_windows():
        return
    for name, schema, handler, description in (
        (
            "codex_voice_start",
            START_SCHEMA,
            handle_codex_voice_start,
            "Launch Codex if needed, create a fresh task, start Voice, and verify ready.",
        ),
        (
            "codex_voice_status",
            STATUS_SCHEMA,
            handle_codex_voice_status,
            "Return inactive, starting, ready, stopping, or failed.",
        ),
        (
            "codex_voice_stop",
            STOP_SCHEMA,
            handle_codex_voice_stop,
            "Stop Voice and leave the Codex task open.",
        ),
    ):
        ctx.register_tool(
            name=name,
            toolset="hermes_voice",
            schema=schema,
            handler=handler,
            check_fn=check_windows,
            description=description,
        )
    ctx.register_skill("codex_voice", Path(__file__).parent / "SKILL.md")
