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


class StartStatusStopTests(unittest.TestCase):
    def test_start_ready_is_idempotent(self):
        ctrl, ui, _launcher = _controller()
        first = ctrl.start({"mode": "new"})
        second = ctrl.start({"mode": "new"})
        self.assertEqual(first, {"ok": True, "status": "ready"})
        self.assertEqual(second, {"ok": True, "status": "ready"})
        self.assertEqual(ui.new_task_calls, 1)

    def test_conflicting_unowned_voice_fails(self):
        ctrl, _ui, _launcher = _controller(unowned_voice=True)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["error"], "conflicting_voice")
        self.assertFalse(result["ok"])

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

    def test_unselected_cable_mic_fails(self):
        ctrl, ui, _launcher = _controller(select_ok=False)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["error"], "cable_mic_not_selected")
        self.assertGreaterEqual(ui.select_calls, 1)
        self.assertGreaterEqual(ui.voice_stop_calls, 1)
        self.assertFalse(ui.voice_is_ready)
        self.assertFalse(ctrl.session.owned)
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)

    def test_process_alone_is_not_voice_ready(self):
        ctrl, _ui, _launcher = _controller(ready_after_start=False)
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["error"], "voice_not_ready")
        self.assertEqual(ctrl.status()["status"], "failed")

    def test_stop_leaves_task_and_does_not_kill(self):
        ctrl, ui, _launcher = _controller()
        ctrl.start({"mode": "new"})
        result = ctrl.stop()
        self.assertEqual(result, {"ok": True, "status": "inactive"})
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)
        self.assertEqual(ui.new_task_calls, 1)

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
        self.assertEqual(result, {"ok": True, "status": "ready"})

    def test_reuse_skips_activate_when_desktop_present(self):
        ctrl, _ui, launcher = _controller()
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result["status"], "ready")
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

    def test_cable_select_success_after_voice(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result, {"ok": True, "status": "ready"})
        self.assertGreaterEqual(ui.select_calls, 1)
        self.assertTrue(ui.voice_is_ready)
        self.assertTrue(ctrl.session.owned)

    def test_new_mode_creates_one_fresh_task(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "new"})
        self.assertEqual(result, {"ok": True, "status": "ready"})
        self.assertEqual(ui.new_task_calls, 1)
        self.assertTrue(ctrl.session.created_fresh_task)

    def test_current_mode_creates_no_task(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "current"})
        self.assertEqual(result, {"ok": True, "status": "ready"})
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

    def test_current_mode_still_selects_cable(self):
        ctrl, ui, _launcher = _controller()
        result = ctrl.start({"mode": "current"})
        self.assertEqual(result, {"ok": True, "status": "ready"})
        self.assertEqual(ui.new_task_calls, 0)
        self.assertGreaterEqual(ui.select_calls, 1)
        self.assertTrue(ui.voice_is_ready)
        self.assertTrue(ctrl.session.owned)


class PluginToolTests(unittest.TestCase):
    def test_schemas_have_no_resume_fields(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from hermes_voice.tools import START_SCHEMA, STATUS_SCHEMA, STOP_SCHEMA

        for schema in (START_SCHEMA, STATUS_SCHEMA, STOP_SCHEMA):
            props = schema["parameters"].get("properties", {})
            self.assertFalse(RESUME_KEYS.intersection(props))
            self.assertEqual(schema["parameters"].get("additionalProperties"), False)

    def test_handlers_return_allowlisted_json(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from companion.codex_control import set_controller
        from hermes_voice.tools import handle_codex_voice_start, handle_codex_voice_status, handle_codex_voice_stop

        ctrl, ui, _launcher = _controller()
        set_controller(ctrl)
        started = json.loads(handle_codex_voice_start({"mode": "new"}))
        status = json.loads(handle_codex_voice_status({}))
        stopped = json.loads(handle_codex_voice_stop({}))
        self.assertEqual(started["status"], "ready")
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
        self.assertEqual(names, ["codex_voice_start", "codex_voice_status", "codex_voice_stop"])
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

    def test_skill_infer_ask_list_select_rules(self):
        text = (ROOT / "plugin" / "hermes_voice" / "SKILL.md").read_text(encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
