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

START_SCHEMA: Dict[str, Any] = {
    "name": "codex_voice_start",
    "description": (
        "On this Windows PC, launch the store-signed Codex desktop app if needed, "
        "create a fresh task, start real Voice, and verify Voice is ready. "
        "Does not resume existing tasks and does not accept task IDs or titles."
    ),
    "parameters": _EMPTY_PARAMS,
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
        "Stop Codex Voice and release companion state. Leaves the fresh Codex "
        "task open. Does not delete, cancel, archive, or close the task."
    ),
    "parameters": _EMPTY_PARAMS,
}


def check_windows() -> bool:
    return os.name == "nt"


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


def handle_codex_voice_status(params: Dict[str, Any] | None = None, **kwargs) -> str:
    del params, kwargs
    return _json(_controller().status())


def handle_codex_voice_stop(params: Dict[str, Any] | None = None, **kwargs) -> str:
    del params, kwargs
    return _json(_controller().stop())
