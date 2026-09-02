import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from companion.codex_control import (  # noqa: E402
    BROWSER_URL,
    CodexVoiceController,
    StaticAudioRouter,
    StaticBrowserTransport,
    StaticCable,
    StaticGuard,
    StaticLauncher,
    StaticUi,
    WtsConnect,
    WtsLock,
    RESULT_KEYS,
    RESUME_KEYS,
    allowlisted,
    classify_wts_session,
    pick_unique_enabled,
)

INDEXED_SKILL = ROOT / "skills" / "hermes_voice" / "SKILL.md"
PLUGIN_SKILL = ROOT / "plugin" / "hermes_voice" / "SKILL.md"


def _controller(
    router: StaticAudioRouter | None = None,
    browser: StaticBrowserTransport | None = None,
    **ui_kw,
) -> tuple[CodexVoiceController, StaticUi, StaticLauncher]:
    ui = StaticUi(**ui_kw)
    launcher = StaticLauncher(present=True)
    router = router or StaticAudioRouter()
    browser = browser or StaticBrowserTransport()
    ctrl = CodexVoiceController(
        guard=StaticGuard(),
        launcher=launcher,
        ui=ui,
        cable=StaticCable(True),
        router=router,
        browser=browser,
        sleep=lambda _s: None,
        ready_wait_s=0.0,
        stop_wait_s=0.0,
    )
    return ctrl, ui, launcher


def _start(ctrl: CodexVoiceController, mode: str = "new", transport: str = "physical_mic"):
    return ctrl.start({"mode": mode, "transport": transport})


def _confirm(ctrl: CodexVoiceController) -> dict:
    return ctrl.confirm(
        {"voice_visible": True, "model_verified": True, "effort_verified": True}
    )


class StartStatusStopTests(unittest.TestCase):
    def test_start_ready_is_idempotent(self):
        ctrl, ui, _launcher = _controller()
        first = _start(ctrl)
        self.assertEqual(first, {"ok": True, "status": "starting"})
        self.assertEqual(_confirm(ctrl), {"ok": True, "status": "ready"})
        second = _start(ctrl)
        self.assertEqual(second, {"ok": True, "status": "ready"})
        self.assertEqual(ui.new_task_calls, 0)

    def test_conflicting_unowned_voice_does_not_block_preflight(self):
        ctrl, ui, _launcher = _controller(unowned_voice=True)
        result = _start(ctrl)
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
        result = _start(ctrl)
        self.assertEqual(result["error"], "cable_mic_missing")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(launcher.activate_calls, 0)

    def test_false_voice_confirmation_keeps_starting(self):
        ctrl, ui, _launcher = _controller()
        _start(ctrl)
        result = ctrl.confirm(
            {"voice_visible": False, "model_verified": True, "effort_verified": True}
        )
        self.assertEqual(result["error"], "voice_not_ready")
        self.assertEqual(result["status"], "starting")
        self.assertFalse(ctrl.session.owned)
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)

    def test_stop_leaves_task_and_does_not_kill(self):
        ctrl, ui, _launcher = _controller()
        _start(ctrl)
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
        result = _start(ctrl)
        self.assertEqual(result["error"], "session_locked")
        self.assertEqual(ui.new_task_calls, 0)

    def test_non_windows_refuses(self):
        ctrl, ui, _launcher = _controller()
        ctrl._guard = StaticGuard(windows=False, unlocked=True)
        result = _start(ctrl)
        self.assertEqual(result["error"], "not_windows")
        self.assertEqual(ui.new_task_calls, 0)

    def test_status_keys_are_allowlisted(self):
        ctrl, _ui, _launcher = _controller()
        _start(ctrl)
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
        result = _start(ctrl)
        self.assertEqual(result, {"ok": True, "status": "starting"})

    def test_reuse_skips_activate_when_desktop_present(self):
        ctrl, _ui, launcher = _controller()
        result = _start(ctrl)
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
        result = _start(ctrl)
        self.assertEqual(result, {"ok": True, "status": "starting"})
        self.assertEqual(ui.new_task_calls, 0)
        self.assertTrue(ctrl.session.created_fresh_task)

    def test_current_mode_creates_no_task(self):
        ctrl, ui, _launcher = _controller()
        result = _start(ctrl, mode="current")
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
        started = _start(ctrl)
        self.assertEqual(started, {"ok": True, "status": "starting"})
        self.assertEqual(ui.select_calls, 0)
        self.assertEqual(ui.new_task_calls, 0)
        self.assertNotEqual(started["status"], "ready")
        self.assertNotEqual(started.get("error"), "voice_not_ready")
        denied = ctrl.confirm(
            {"voice_visible": False, "model_verified": True, "effort_verified": True}
        )
        self.assertEqual(denied["status"], "starting")
        self.assertEqual(denied["error"], "voice_not_ready")
        self.assertFalse(ctrl.session.owned)
        confirmed = _confirm(ctrl)
        self.assertEqual(confirmed, {"ok": True, "status": "ready"})

    def test_confirm_from_inactive_is_not_ready(self):
        ctrl, _ui, _launcher = _controller()
        result = _confirm(ctrl)
        self.assertEqual(result["error"], "voice_not_ready")
        self.assertNotEqual(result["status"], "ready")
        self.assertFalse(ctrl.session.owned)

    def test_confirm_requires_visible_voice(self):
        ctrl, _ui, _launcher = _controller()
        _start(ctrl, mode="current")
        missing_voice = ctrl.confirm(
            {"voice_visible": False, "model_verified": True, "effort_verified": True}
        )
        self.assertEqual(missing_voice["error"], "voice_not_ready")
        self.assertEqual(missing_voice["status"], "starting")
        self.assertFalse(ctrl.session.owned)

    def test_start_does_not_invoke_codex_ui(self):
        ctrl, ui, _launcher = _controller()
        result = _start(ctrl)
        self.assertEqual(result["status"], "starting")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(ui.select_calls, 0)
        self.assertEqual(ui.voice_stop_calls, 0)
        self.assertFalse(ui.voice_is_ready)

    def test_stop_clears_without_uia_or_task_close(self):
        ctrl, ui, _launcher = _controller()
        _start(ctrl, mode="current")
        result = ctrl.stop()
        self.assertEqual(result, {"ok": True, "status": "inactive"})
        self.assertEqual(ui.voice_stop_calls, 0)
        self.assertEqual(ui.close_task_calls, 0)
        self.assertEqual(ui.kill_calls, 0)

    def test_start_and_stop_own_audio_router(self):
        router = StaticAudioRouter()
        browser = StaticBrowserTransport()
        ctrl, _ui, _launcher = _controller(router=router, browser=browser)
        self.assertEqual(_start(ctrl)["status"], "starting")
        self.assertTrue(router.running)
        self.assertEqual(router.start_calls, 1)
        self.assertEqual(browser.start_calls, 0)
        confirmed = _confirm(ctrl)
        self.assertEqual(confirmed["status"], "ready")
        self.assertNotIn("url", confirmed)
        self.assertEqual(ctrl.stop()["status"], "inactive")
        self.assertFalse(router.running)
        self.assertEqual(router.stop_calls, 1)
        self.assertEqual(browser.stop_calls, 0)

    def test_router_start_failure_fails_closed(self):
        router = StaticAudioRouter(start_ok=False)
        ctrl, _ui, _launcher = _controller(router=router)
        result = _start(ctrl, mode="current")
        self.assertEqual(result, {"ok": False, "status": "failed", "error": "audio_bridge_failed"})

    def test_status_detects_router_drop(self):
        router = StaticAudioRouter()
        ctrl, _ui, _launcher = _controller(router=router)
        _start(ctrl, mode="current")
        _confirm(ctrl)
        router.running = False
        self.assertEqual(ctrl.status()["error"], "audio_bridge_failed")

    def test_confirm_requires_model_and_effort_verification(self):
        ctrl, _ui, _launcher = _controller()
        _start(ctrl)
        missing_model = ctrl.confirm(
            {"voice_visible": True, "model_verified": False, "effort_verified": True}
        )
        self.assertEqual(missing_model["error"], "model_not_verified")
        self.assertEqual(missing_model["status"], "starting")
        missing_effort = ctrl.confirm(
            {"voice_visible": True, "model_verified": True, "effort_verified": False}
        )
        self.assertEqual(missing_effort["error"], "effort_not_verified")
        self.assertEqual(missing_effort["status"], "starting")


class TransportSelectionTests(unittest.TestCase):
    def test_transport_is_required(self):
        ctrl, ui, launcher = _controller()
        missing = ctrl.start({"mode": "new"})
        invalid = ctrl.start({"mode": "new", "transport": "discord"})
        self.assertEqual(missing["error"], "transport_required")
        self.assertEqual(invalid["error"], "transport_required")
        self.assertEqual(ui.new_task_calls, 0)
        self.assertEqual(launcher.activate_calls, 0)

    def test_physical_results_never_include_url(self):
        ctrl, _ui, _launcher = _controller()
        started = _start(ctrl, transport="physical_mic")
        status_starting = ctrl.status()
        confirmed = _confirm(ctrl)
        status_ready = ctrl.status()
        for payload in (started, status_starting, confirmed, status_ready):
            self.assertNotIn("url", payload)
        self.assertNotIn("url", allowlisted(True, "ready", url="http://evil.example/"))

    def test_browser_start_does_not_start_physical_router(self):
        router = StaticAudioRouter()
        browser = StaticBrowserTransport()
        ctrl, _ui, _launcher = _controller(router=router, browser=browser)
        started = _start(ctrl, transport="browser")
        self.assertEqual(started, {"ok": True, "status": "starting"})
        self.assertNotIn("url", started)
        self.assertTrue(browser.running)
        self.assertEqual(browser.start_calls, 1)
        self.assertFalse(router.running)
        self.assertEqual(router.start_calls, 0)
        confirmed = _confirm(ctrl)
        self.assertEqual(confirmed, {"ok": True, "status": "ready", "url": BROWSER_URL})
        status = ctrl.status()
        self.assertEqual(status["url"], BROWSER_URL)
        self.assertEqual(ctrl.stop()["status"], "inactive")
        self.assertFalse(browser.running)
        self.assertEqual(browser.stop_calls, 1)
        self.assertEqual(router.stop_calls, 0)
        self.assertNotIn("url", ctrl.status())

    def test_same_transport_start_is_idempotent(self):
        browser = StaticBrowserTransport()
        ctrl, _ui, _launcher = _controller(browser=browser)
        self.assertEqual(_start(ctrl, transport="browser")["status"], "starting")
        again = _start(ctrl, transport="browser")
        self.assertEqual(again["status"], "starting")
        self.assertEqual(browser.start_calls, 1)
        _confirm(ctrl)
        ready_again = _start(ctrl, transport="browser")
        self.assertEqual(ready_again, {"ok": True, "status": "ready", "url": BROWSER_URL})
        self.assertEqual(browser.start_calls, 1)

    def test_switching_transport_fails_closed(self):
        router = StaticAudioRouter()
        browser = StaticBrowserTransport()
        ctrl, _ui, _launcher = _controller(router=router, browser=browser)
        self.assertEqual(_start(ctrl, transport="physical_mic")["status"], "starting")
        switched = _start(ctrl, transport="browser")
        self.assertEqual(switched["error"], "transport_conflict")
        self.assertEqual(switched["status"], "starting")
        self.assertTrue(router.running)
        self.assertEqual(browser.start_calls, 0)
        _confirm(ctrl)
        switched_ready = _start(ctrl, transport="browser")
        self.assertEqual(switched_ready["error"], "transport_conflict")
        self.assertEqual(switched_ready["status"], "ready")
        self.assertNotIn("url", switched_ready)
        self.assertTrue(router.running)
        self.assertFalse(browser.running)

    def test_browser_dead_server_is_detected(self):
        browser = StaticBrowserTransport()
        ctrl, _ui, _launcher = _controller(browser=browser)
        _start(ctrl, transport="browser")
        _confirm(ctrl)
        browser.running = False
        status = ctrl.status()
        self.assertEqual(status["error"], "audio_bridge_failed")
        self.assertEqual(status["status"], "failed")
        self.assertNotIn("url", status)

    def test_missing_browser_dependencies_fail_closed(self):
        router = StaticAudioRouter()
        browser = StaticBrowserTransport(
            start_ok=False, failure="browser_dependency_missing"
        )
        ctrl, _ui, _launcher = _controller(router=router, browser=browser)
        result = _start(ctrl, transport="browser")
        self.assertEqual(
            result,
            {"ok": False, "status": "failed", "error": "browser_dependency_missing"},
        )
        self.assertFalse(router.running)
        self.assertEqual(router.start_calls, 0)

    def test_injected_url_is_ignored(self):
        browser = StaticBrowserTransport()
        ctrl, _ui, _launcher = _controller(browser=browser)
        started = ctrl.start(
            {
                "mode": "new",
                "transport": "browser",
                "url": "http://evil.example/",
            }
        )
        self.assertNotIn("url", started)
        confirmed = ctrl.confirm(
            {
                "voice_visible": True,
                "model_verified": True,
                "effort_verified": True,
                "url": "http://evil.example/",
            }
        )
        self.assertEqual(confirmed["url"], BROWSER_URL)
        self.assertNotEqual(confirmed["url"], "http://evil.example/")

    def test_codex_control_source_does_not_import_browser_extras(self):
        source = (ROOT / "companion" / "codex_control.py").read_text(encoding="utf-8")
        self.assertNotIn("aiohttp", source)
        self.assertNotIn("aiortc", source)
        self.assertNotIn("from companion.browser_call.server", source)


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
        started = json.loads(
            handle_codex_voice_start({"mode": "new", "transport": "physical_mic"})
        )
        confirmed = json.loads(
            handle_codex_voice_confirm(
                {"voice_visible": True, "model_verified": True, "effort_verified": True}
            )
        )
        status = json.loads(handle_codex_voice_status({}))
        stopped = json.loads(handle_codex_voice_stop({}))
        self.assertEqual(started["status"], "starting")
        self.assertNotIn("url", started)
        self.assertEqual(confirmed["status"], "ready")
        self.assertNotIn("url", confirmed)
        self.assertEqual(status["status"], "ready")
        self.assertNotIn("url", status)
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
        self.assertEqual(set(params["properties"]), {"mode", "transport"})
        self.assertEqual(set(params["required"]), {"mode", "transport"})
        self.assertEqual(set(params["properties"]["mode"]["enum"]), {"new", "current"})
        self.assertEqual(
            set(params["properties"]["transport"]["enum"]), {"physical_mic", "browser"}
        )
        self.assertEqual(params.get("additionalProperties"), False)

    def test_confirm_schema_requires_voice_model_and_effort(self):
        plugin_root = ROOT / "plugin" / "hermes_voice"
        if str(plugin_root.parent) not in sys.path:
            sys.path.insert(0, str(plugin_root.parent))
        from hermes_voice.tools import CONFIRM_SCHEMA

        params = CONFIRM_SCHEMA["parameters"]
        expected = {"voice_visible", "model_verified", "effort_verified"}
        self.assertEqual(set(params["properties"]), expected)
        self.assertEqual(set(params["required"]), expected)

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
        self.assertIn("transport", lowered)
        self.assertIn("physical_mic", text)
        self.assertIn("browser", lowered)
        self.assertIn("http://127.0.0.1:8765/", text)
        self.assertIn("leave call", lowered)
        self.assertIn("pc microphone", lowered)

    def test_skill_uses_setup_time_cable_and_runtime_voice(self):
        text = INDEXED_SKILL.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("computer_use", text)
        self.assertIn("codex_voice_confirm", text)
        self.assertIn("cable output", lowered)
        self.assertIn("slash command", lowered)
        self.assertIn("one-time setup", lowered)
        self.assertIn("do not attempt per-call device selection", lowered)

    def test_skill_requires_explicit_model_and_effort_each_start(self):
        text = INDEXED_SKILL.read_text(encoding="utf-8").lower()
        self.assertIn("every voice start", text)
        self.assertIn("ask the user", text)
        self.assertIn("model_verified=true", text)
        self.assertIn("effort_verified=true", text)
        self.assertIn("re-check", text)

    def test_indexed_skill_matches_plugin_skill(self):
        indexed = INDEXED_SKILL.read_text(encoding="utf-8")
        plugin = PLUGIN_SKILL.read_text(encoding="utf-8")
        self.assertEqual(indexed, plugin)
        self.assertTrue(INDEXED_SKILL.is_file())


if __name__ == "__main__":
    unittest.main()
