"""Register same-host Codex Voice tools with the current Hermes plugin API."""

from __future__ import annotations

from .tools import (
    CONFIRM_SCHEMA,
    START_SCHEMA,
    STATUS_SCHEMA,
    STOP_SCHEMA,
    check_windows,
    handle_codex_voice_confirm,
    handle_codex_voice_start,
    handle_codex_voice_status,
    handle_codex_voice_stop,
    skill_markdown_path,
)


def register(ctx) -> None:
    if not check_windows():
        return
    for name, schema, handler, description in (
        (
            "codex_voice_start",
            START_SCHEMA,
            handle_codex_voice_start,
            "When the user asks to start or resume Codex Voice, preflight and launch Codex, then start the configured physical-mic audio route. Ask for model and effort, use computer_use, then confirm.",
        ),
        (
            "codex_voice_confirm",
            CONFIRM_SCHEMA,
            handle_codex_voice_confirm,
            "After computer_use shows Voice active and verifies the chosen model and effort after startup, record ready.",
        ),
        (
            "codex_voice_status",
            STATUS_SCHEMA,
            handle_codex_voice_status,
            "Return inactive, starting, ready, stopping, or failed for Codex Voice on this PC.",
        ),
        (
            "codex_voice_stop",
            STOP_SCHEMA,
            handle_codex_voice_stop,
            "After computer_use ended Codex Voice, stop the audio route, clear state, and leave the Codex task open.",
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
    ctx.register_skill("codex_voice", skill_markdown_path())
