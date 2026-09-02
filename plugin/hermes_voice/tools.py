"""Hermes tool schemas and handlers for Codex Voice."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict

_EMPTY_PARAMS: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

_MODE_PARAMS: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["new", "current"],
            "description": (
                "new: preflight then the skill creates a fresh Codex conversation "
                "with computer_use. current: preflight then the skill uses the "
                "conversation already selected in Codex."
            ),
        }
    },
    "required": ["mode"],
    "additionalProperties": False,
}

_CONFIRM_PARAMS: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "voice_visible": {
            "type": "boolean",
            "description": (
                "True only after app-scoped computer_use showed Voice is visibly active."
            ),
        },
        "cable_selected": {
            "type": "boolean",
            "description": (
                "True only after app-scoped computer_use selected and verified "
                "CABLE Output (VB-Audio Virtual Cable)."
            ),
        },
    },
    "required": ["voice_visible", "cable_selected"],
    "additionalProperties": False,
}

START_SCHEMA: Dict[str, Any] = {
    "name": "codex_voice_start",
    "description": (
        "On this Windows PC, preflight the unlocked session, launch the store-signed "
        "Codex desktop app if needed, and prove VB-CABLE capture is present. "
        "Returns starting. Does not click Voice, create a task, or select the microphone. "
        "After computer_use finishes Voice and CABLE Output, call codex_voice_confirm. "
        "mode=new is a new conversation. mode=current is the selected conversation. "
        "Does not accept task IDs, titles, or App Server resume keys."
    ),
    "parameters": _MODE_PARAMS,
}

CONFIRM_SCHEMA: Dict[str, Any] = {
    "name": "codex_voice_confirm",
    "description": (
        "Record Codex Voice ready after computer_use verified Voice is visible and "
        "CABLE Output (VB-Audio Virtual Cable) is selected. Call only while status is "
        "starting. Both voice_visible and cable_selected must be true. "
        "Does not inspect conversation contents."
    ),
    "parameters": _CONFIRM_PARAMS,
}

STATUS_SCHEMA: Dict[str, Any] = {
    "name": "codex_voice_status",
    "description": (
        "Return the owned Codex Voice lifecycle state: inactive, starting, "
        "ready, stopping, or failed. No task content is returned."
    ),
    "parameters": _EMPTY_PARAMS,
}

STOP_SCHEMA: Dict[str, Any] = {
    "name": "codex_voice_stop",
    "description": (
        "Clear companion Voice session state after computer_use ended Voice and "
        "verified it ended. Leaves the Codex task open. Does not delete, cancel, "
        "archive, or close the task."
    ),
    "parameters": _EMPTY_PARAMS,
}


def check_windows() -> bool:
    return os.name == "nt"


def skill_markdown_path() -> Path:
    here = Path(__file__).resolve().parent
    indexed = here.parents[1] / "skills" / "hermes_voice" / "SKILL.md"
    if indexed.is_file():
        return indexed
    return here / "SKILL.md"


def _controller():
    here = Path(__file__).resolve().parent
    for root in (here.parents[1], here):
        if (root / "companion" / "codex_control.py").is_file():
            path = str(root)
            if path not in sys.path:
                sys.path.insert(0, path)
            break
    from companion.codex_control import default_controller

    return default_controller()


def _json(result: dict[str, Any]) -> str:
    from companion.codex_control import dumps_result

    return dumps_result(result)


def handle_codex_voice_start(params: Dict[str, Any] | None = None, **kwargs) -> str:
    del kwargs
    return _json(_controller().start(params or {}))


def handle_codex_voice_confirm(params: Dict[str, Any] | None = None, **kwargs) -> str:
    del kwargs
    return _json(_controller().confirm(params or {}))


def handle_codex_voice_status(params: Dict[str, Any] | None = None, **kwargs) -> str:
    del params, kwargs
    return _json(_controller().status())


def handle_codex_voice_stop(params: Dict[str, Any] | None = None, **kwargs) -> str:
    del params, kwargs
    return _json(_controller().stop())
