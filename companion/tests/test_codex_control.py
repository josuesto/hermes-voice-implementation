import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from companion.codex_control import (  # noqa: E402
    CodexVoiceController,
    StaticCable,
    StaticGuard,
    StaticLauncher,
    StaticUi,
    WtsConnect,
    WtsLock,
    RESULT_KEYS,
    RESUME_KEYS,
    classify_wts_session,
    pick_unique_enabled,
)

INDEXED_SKILL = ROOT / "skills" / "hermes_voice" / "SKILL.md"
PLUGIN_SKILL = ROOT / "plugin" / "hermes_voice" / "SKILL.md"


def _controller(**ui_kw) -> tuple[CodexVoiceController, StaticUi, StaticLauncher]:
    ui = StaticUi(**ui_kw)
    launcher = StaticLauncher(present=True)
    ctrl = CodexVoiceController(
        guard=StaticGuard(),
        launcher=launcher,
        ui=ui,
        cable=StaticCable(True),
        sleep=lambda _s: None,
        ready_wait_s=0.0,
        stop_wait_s=0.0,
    )
    return ctrl, ui, launcher


def _confirm(ctrl: CodexVoiceController) -> dict:
    return ctrl.confirm({"voice_visible": True, "cable_selected": True})


class StartStatusStopTests(unittest.TestCase):
    def test_start_ready_is_idempotent(self):
        ctrl, ui, _launcher = _controller()
        first = ctrl.start({"mode": "new"})
        self.assertEqual(first, {"ok": True, "status": "starting"})
        self.assertEqual(_confirm(ctrl), {"ok": True, "status": "ready"})
        second = ctrl.start({"mode": "new"})
        self.assertEqual(second, {"ok": True, "status": "ready"})
        self.assertEqual(ui.new_task_calls, 0)

    def test_conflicting_unowned_voice_does_not_block_preflight(self):
        ctrl, ui, _launcher = _controller(unowned_voice=True)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result, {"ok": True, "status": "starting"})
        self.assertEqual(ui.new_task_calls, 0)

    def test_resume_params_are_refused(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"task_id": "secret"})
        self.assertEqual(result["error"], "resume_unsupported")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertTrue(RESUME_KEYS)

    def test_missing_cable_fails(self):
        ctrl, ui, launcher = _controller()
        ctrl._cable = StaticCable(False)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["error"], "cable_mic_missing")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(launcher.activate_calls, 0)

    def test_unselected_cable_keeps_starting(self):
        ctrl, ui, _launcher = _controller()
        ctrl.start({"mode": "new"})
        result = ctrl.confirm({"voice_visible": True, "cable_selected": False})
        self.assertEqual(result["error"], "cable_mic_not_selected")
        self.assertEqual(result["status"], "starting")
        self.assertFalse(ctrl.session.owned)
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)

    def test_stop_leaves_task_and_does_not_kill(self):
        ctrl, ui, _launcher = _controller()
        ctrl.start({"mode": "new"})
        _confirm(ctrl)
        result = ctrl.stop()
        self.assertEqual(result, {"ok": True, "status": "inactive"})
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(ui.voice_stop_calls, 0)

    def test_locked_session_refuses(self):
        ctrl, ui, _launcher = _controller()
        ctrl._guard = StaticGuard(windows=True, unlocked=False)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["error"], "session_locked")
        self.assertEqual(ui.new_task_calls, 0)

    def test_non_windows_refuses(self):
        ctrl, ui, _launcher = _controller()
        ctrl._guard = StaticGuard(windows=False, unlocked=True)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["error"], "not_windows")
        self.assertEqual(ui.new_task_calls, 0)

    def test_status_keys_are_allowlisted(self):
        ctrl, _ui, _launcher = _controller()
        ctrl.start({"mode": "new"})
        payload = ctrl.status()
        self.assertEqual(set(payload), set(RESULT_KEYS) & set(payload))
        for key in payload:
            self.assertIn(key, RESULT_KEYS)

    def test_launch_when_desktop_absent(self):
        ctrl, ui, launcher = _controller()
        launcher.present = False
        ui.window = False

        def activate() -> bool:
            launcher.present = True
            ui.window = True
            return True

        launcher.activate = activate  # type: ignore[method-assign]
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result, {"ok": True, "status": "starting"})

    def test_reuse_skips_activate_when_desktop_present(self):
        ctrl, _ui, launcher = _controller()
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["status"], "starting")
        self.assertEqual(launcher.activate_calls, 0)

    def test_scoped_lookup_ignores_other_window_names(self):
        unique = pick_unique_enabled(
            [
                {"enabled": True, "in_scope": False, "name": "Voice"},
                {"enabled": False, "in_scope": True, "name": "Voice"},
                {"enabled": True, "in_scope": True, "name": "Voice"},
            ]
        )
        self.assertEqual(unique["name"], "Voice")
        self.assertTrue(unique["in_scope"])
        self.assertIsNone(
            pick_unique_enabled(
                [
                    {"enabled": True, "in_scope": False, "name": "Voice"},
                    {"enabled": True, "in_scope": True, "name": "Voice"},
                    {"enabled": True, "in_scope": True, "name": "Voice"},
                ]
            )
        )
        self.assertIsNone(
            pick_unique_enabled(
                [
                    {"enabled": True, "in_scope": False, "name": "Voice"},
                    {"enabled": False, "in_scope": True, "name": "Voice"},
                ]
            )
        )

    def test_wts_unknown_is_not_unlocked(self):
        locked = WtsLock(
            ok=True,
            bytes_returned=20,
            level=1,
            session_id=1,
            session_state=0,
            session_flags=1,
        )
        short = classify_wts_session(
            WtsConnect(ok=True, bytes_returned=2, session_id=1, session_state=0),
            locked,
            1,
        )
        missing_id = classify_wts_session(
            WtsConnect(ok=True, bytes_returned=4, session_id=None, session_state=0),
            locked,
            1,
        )
        disagree = classify_wts_session(
            WtsConnect(ok=True, bytes_returned=4, session_id=1, session_state=0),
            WtsLock(ok=True, bytes_returned=20, level=1, session_id=1, session_state=4, session_flags=1),
            1,
        )
        self.assertEqual(short, "unknown")
        self.assertEqual(missing_id, "unknown")
        self.assertEqual(disagree, "unknown")
        self.assertNotEqual(short, "active-unlocked")

    def test_wts_locked_is_not_unlocked(self):
        result = classify_wts_session(
            WtsConnect(ok=True, bytes_returned=4, session_id=1, session_state=0),
            WtsLock(ok=True, bytes_returned=20, level=1, session_id=1, session_state=0, session_flags=0),
            1,
            "modern",
        )
        self.assertEqual(result, "locked-or-disconnected")
        self.assertNotEqual(result, "active-unlocked")

    def test_new_mode_does_not_click_new_task(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result, {"ok": True, "status": "starting"})
        self.assertEqual(ui.new_task_calls, 0)
        self.assertTrue(ctrl.session.created_fresh_task)

    def test_current_mode_creates_no_task(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "current"})
        self.assertEqual(result, {"ok": True, "status": "starting"})
        self.assertEqual(ui.new_task_calls, 0)
        self.assertFalse(ctrl.session.created_fresh_task)
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)

    def test_missing_or_invalid_mode_fails_before_ui(self):
        ctrl, ui, launcher = _controller()
        missing = ctrl.start({})
        invalid = ctrl.start({"mode": "resume"})
        self.assertEqual(missing["error"], "mode_required")
        self.assertEqual(invalid["error"], "mode_required")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(ui.select_calls, 0)
        self.assertEqual(launcher.activate_calls, 0)

    def test_uia_ready_false_negative_does_not_skip_confirm(self):
        ctrl, ui, _launcher = _controller(ready_after_start=False)
        started = ctrl.start({"mode": "new"})
        self.assertEqual(started, {"ok": True, "status": "starting"})
        self.assertEqual(ui.select_calls, 0)
        self.assertEqual(ui.new_task_calls, 0)
        self.assertNotEqual(started["status"], "ready")
        self.assertNotEqual(started.get("error"), "voice_not_ready")
        denied = ctrl.confirm({"voice_visible": True, "cable_selected": False})
        self.assertEqual(denied["status"], "starting")
        self.assertEqual(denied["error"], "cable_mic_not_selected")
        self.assertFalse(ctrl.session.owned)
        confirmed = _confirm(ctrl)
        self.assertEqual(confirmed, {"ok": True, "status": "ready"})

    def test_confirm_from_inactive_is_not_ready(self):
        ctrl, _ui, _launcher = _controller()
        result = _confirm(ctrl)
        self.assertEqual(result["error"], "voice_not_ready")
        self.assertNotEqual(result["status"], "ready")
        self.assertFalse(ctrl.session.owned)

    def test_confirm_requires_voice_and_cable(self):
        ctrl, _ui, _launcher = _controller()
        ctrl.start({"mode": "current"})
        missing_voice = ctrl.confirm({"voice_visible": False, "cable_selected": True})
        missing_cable = ctrl.confirm({"voice_visible": True, "cable_selected": False})
        self.assertEqual(missing_voice["error"], "voice_not_ready")
        self.assertEqual(missing_voice["status"], "starting")
        self.assertEqual(missing_cable["error"], "cable_mic_not_selected")
        self.assertEqual(missing_cable["status"], "starting")
        self.assertFalse(ctrl.session.owned)

    def test_start_does_not_invoke_codex_ui(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["status"], "starting")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(ui.select_calls, 0)
        self.assertEqual(ui.voice_stop_calls, 0)
        self.assertFalse(ui.voice_is_ready)

    def test_stop_clears_without_uia_or_task_close(self):
        ctrl, ui, _launcher = _controller()
        ctrl.start({"mode": "current"})
        result = ctrl.stop()
        self.assertEqual(result, {"ok": True, "status": "inactive"})
        self.assertEqual(ui.voice_stop_calls, 0)
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)


class PluginToolTests(unittest.TestCase):
    def test_schemas_have_no_resume_fields(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from hermes_voice.tools import CONFIRM_SCHEMA, START_SCHEMA, STATUS_SCHEMA, STOP_SCHEMA

        for schema in (START_SCHEMA, CONFIRM_SCHEMA, STATUS_SCHEMA, STOP_SCHEMA):
            props = schema["parameters"].get("properties", {})
            self.assertFalse(RESUME_KEYS.intersection(props))
            self.assertEqual(schema["parameters"].get("additionalProperties"), False)

    def test_handlers_return_allowlisted_json(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from companion.codex_control import set_controller
        from hermes_voice.tools import (
            handle_codex_voice_confirm,
            handle_codex_voice_start,
            handle_codex_voice_status,
            handle_codex_voice_stop,
        )

        ctrl, ui, _launcher = _controller()
        set_controller(ctrl)
        started = json.loads(handle_codex_voice_start({"mode": "new"}))
        confirmed = json.loads(
            handle_codex_voice_confirm({"voice_visible": True, "cable_selected": True})
        )
        status = json.loads(handle_codex_voice_status({}))
        stopped = json.loads(handle_codex_voice_stop({}))
        self.assertEqual(started["status"], "starting")
        self.assertEqual(confirmed["status"], "ready")
        self.assertEqual(status["status"], "ready")
        self.assertEqual(stopped["status"], "inactive")
        self.assertEqual(ui.close_task_calls, 0)
        set_controller(None)

    def test_register_uses_ctx_register_tool(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        import hermes_voice

        ctx = MagicMock()
        hermes_voice.register(ctx)
        names = [call.kwargs["name"] for call in ctx.register_tool.call_args_list]
        self.assertEqual(
            names,
            ["codex_voice_start", "codex_voice_confirm", "codex_voice_status", "codex_voice_stop"],
        )
        for call in ctx.register_tool.call_args_list:
            self.assertEqual(call.kwargs["toolset"], "hermes_voice")
            self.assertIn("schema", call.kwargs)
            self.assertIn("handler", call.kwargs)
        ctx.register_skill.assert_called_once()
        ctx.register_hook.assert_not_called()

    def test_start_schema_exposes_only_new_and_current(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from hermes_voice.tools import START_SCHEMA

        params = START_SCHEMA["parameters"]
        self.assertEqual(set(params["properties"]), {"mode"})
        self.assertEqual(params["required"], ["mode"])
        self.assertEqual(set(params["properties"]["mode"]["enum"]), {"new", "current"})
        self.assertEqual(params.get("additionalProperties"), False)

    def test_confirm_schema_requires_voice_and_cable(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from hermes_voice.tools import CONFIRM_SCHEMA

        params = CONFIRM_SCHEMA["parameters"]
        self.assertEqual(set(params["properties"]), {"voice_visible", "cable_selected"})
        self.assertEqual(set(params["required"]), {"voice_visible", "cable_selected"})

    def test_skill_infer_ask_list_select_rules(self):
        text = INDEXED_SKILL.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("infer", lowered)
        self.assertIn("ask", lowered)
        self.assertIn("numbered list", lowered)
        self.assertIn("computer_use", text)
        self.assertIn('mode="ax"', text)
        self.assertIn('mode="new"', text)
        self.assertIn('mode="current"', text)
        self.assertIn("ambiguous", lowered)
        self.assertIn("do not guess", lowered)
        self.assertIn("never use raw coordinates", lowered)

    def test_skill_computer_use_owns_voice_and_cable(self):
        text = INDEXED_SKILL.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("computer_use", text)
        self.assertIn("codex_voice_confirm", text)
        self.assertIn("cable output", lowered)
        self.assertIn("slash command", lowered)
        self.assertIn("microphone selection", lowered)

    def test_indexed_skill_matches_plugin_skill(self):
        indexed = INDEXED_SKILL.read_text(encoding="utf-8")
        plugin = PLUGIN_SKILL.read_text(encoding="utf-8")
        self.assertEqual(indexed, plugin)
        self.assertTrue(INDEXED_SKILL.is_file())


if __name__ == "__main__":
    unittest.main()
