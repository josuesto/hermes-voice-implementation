"""Owned Codex Voice lifecycle for same-host Hermes.

Launch uses packaged activation only. Fresh-task (mode=new) and Voice
actions use semantic UI Automation names scoped to one verified Codex
window. mode=current skips task creation. Status and errors are
allowlisted. Task titles, IDs, prompts, audio, and accessibility trees
are never persisted.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

STATUSES = ("inactive", "starting", "ready", "stopping", "failed")
ERRORS = (
    "not_windows",
    "session_locked",
    "resume_unsupported",
    "conflicting_voice",
    "cable_mic_missing",
    "cable_mic_not_selected",
    "launch_failed",
    "fresh_task_failed",
    "voice_start_failed",
    "voice_not_ready",
    "stop_failed",
    "mode_required",
)
RESULT_KEYS = ("ok", "status", "error")
RESUME_KEYS = frozenset({"task_id", "thread_id", "title", "resume", "task_title"})
START_MODES = ("new", "current")
CABLE_MIC_NAME = "CABLE Output (VB-Audio Virtual Cable)"
NEW_TASK_NAMES = ("New task", "New chat", "New thread")
VOICE_START_NAMES = ("Voice", "Start voice", "Voice mode")
VOICE_READY_NAMES = ("Stop voice", "End voice", "Mute microphone")
VOICE_STOP_NAMES = ("Stop voice", "End voice")
MIC_OPEN_NAMES = ("Microphone", "Voice settings", "Audio settings", "Input device")
MAIN_UI_PROCESS = "chatgpt.exe"
CHROMIUM_CLASS_PREFIX = "Chrome_WidgetWin"
PACKAGE_NAME = "OpenAI.Codex"
READY_WAIT_SECONDS = 12.0
STOP_WAIT_SECONDS = 8.0
WTS_ACTIVE = 0
WTS_DISCONNECTED = 4
WTS_CONNECTSTATE = 8
WTS_SESSION_INFO_EX = 25
CONNECT_MIN_BYTES = 4
LOCK_MIN_BYTES = 20
WTS_UNLOCK_FLAG = 1
WTS_LOCK_FLAG = 0


class SessionGuard(Protocol):
    def is_windows(self) -> bool: ...
    def is_interactive_unlocked(self) -> bool: ...


class PackageLauncher(Protocol):
    def desktop_present(self) -> bool: ...
    def activate(self) -> bool: ...


class DesktopUi(Protocol):
    def main_window_present(self) -> bool: ...
    def unowned_voice_active(self) -> bool: ...
    def invoke_new_task(self) -> bool: ...
    def invoke_voice_start(self) -> bool: ...
    def voice_ready(self) -> bool: ...
    def invoke_voice_stop(self) -> bool: ...
    def select_cable_mic(self) -> bool: ...
    def close_or_delete_task(self) -> None: ...
    def kill_codex(self) -> None: ...


class CableMic(Protocol):
    def output_present(self) -> bool: ...


@dataclass(frozen=True)
class WtsConnect:
    ok: bool
    bytes_returned: int
    session_id: int | None
    session_state: int | None


@dataclass(frozen=True)
class WtsLock:
    ok: bool
    bytes_returned: int
    level: int | None
    session_id: int | None
    session_state: int | None
    session_flags: int | None


def classify_wts_session(
    connect: WtsConnect,
    lock: WtsLock,
    process_session_id: int,
    contract: str = "modern",
) -> str:
    """Return active-unlocked, locked-or-disconnected, or unknown."""
    connect_sized = bool(connect.ok) and connect.bytes_returned >= CONNECT_MIN_BYTES
    lock_sized = bool(lock.ok) and lock.bytes_returned >= LOCK_MIN_BYTES
    if not connect_sized or not lock_sized:
        return "unknown"
    if lock.level != 1:
        return "unknown"
    if connect.session_id is None or lock.session_id is None:
        return "unknown"
    if connect.session_id != process_session_id or lock.session_id != process_session_id:
        return "unknown"
    if connect.session_state != lock.session_state:
        return "unknown"
    cs = connect.session_state
    flags = lock.session_flags
    if cs == WTS_DISCONNECTED:
        if contract == "modern" and flags == WTS_UNLOCK_FLAG:
            return "unknown"
        return "locked-or-disconnected"
    if cs != WTS_ACTIVE or lock.session_state != WTS_ACTIVE or contract != "modern" or flags == -1:
        return "unknown"
    if flags == WTS_LOCK_FLAG:
        return "locked-or-disconnected"
    if flags == WTS_UNLOCK_FLAG:
        return "active-unlocked"
    return "unknown"


def pick_unique_enabled(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Keep only in-scope enabled controls. Require exactly one."""
    hits = [row for row in candidates if row.get("in_scope") and row.get("enabled")]
    if len(hits) != 1:
        return None
    return hits[0]


def allowlisted(ok: bool, status: str, error: str | None = None) -> dict[str, Any]:
    if status not in STATUSES:
        status = "failed"
        error = error or "voice_not_ready"
    payload: dict[str, Any] = {"ok": bool(ok), "status": status}
    if error:
        payload["error"] = error if error in ERRORS else "voice_not_ready"
    return {key: payload[key] for key in RESULT_KEYS if key in payload}


@dataclass
class Session:
    status: str = "inactive"
    owned: bool = False
    created_fresh_task: bool = False


class CodexVoiceController:
    def __init__(
        self,
        *,
        guard: SessionGuard,
        launcher: PackageLauncher,
        ui: DesktopUi,
        cable: CableMic,
        sleep: Callable[[float], None] = time.sleep,
        ready_wait_s: float = READY_WAIT_SECONDS,
        stop_wait_s: float = STOP_WAIT_SECONDS,
    ) -> None:
        self._guard = guard
        self._launcher = launcher
        self._ui = ui
        self._cable = cable
        self._sleep = sleep
        self._ready_wait_s = ready_wait_s
        self._stop_wait_s = stop_wait_s
        self.session = Session()

    def status(self) -> dict[str, Any]:
        if self.session.owned and self.session.status == "ready" and not self._ui.voice_ready():
            self.session.status = "failed"
            return allowlisted(False, "failed", "voice_not_ready")
        return allowlisted(self.session.status != "failed", self.session.status)

    def start(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = params or {}
        if RESUME_KEYS.intersection(params):
            self.session.status = "failed"
            return allowlisted(False, "failed", "resume_unsupported")
        mode = params.get("mode")
        if mode not in START_MODES:
            self.session.status = "failed"
            return allowlisted(False, "failed", "mode_required")
        if not self._guard.is_windows():
            self.session.status = "failed"
            return allowlisted(False, "failed", "not_windows")
        if not self._guard.is_interactive_unlocked():
            self.session.status = "failed"
            return allowlisted(False, "failed", "session_locked")
        if self.session.owned and self.session.status == "ready" and self._ui.voice_ready():
            return allowlisted(True, "ready")
        if self._ui.unowned_voice_active() and not self.session.owned:
            self.session.status = "failed"
            return allowlisted(False, "failed", "conflicting_voice")
        if not self._cable.output_present():
            self.session.status = "failed"
            return allowlisted(False, "failed", "cable_mic_missing")

        self.session.status = "starting"
        if not self._launcher.desktop_present():
            if not self._launcher.activate():
                self.session.status = "failed"
                return allowlisted(False, "failed", "launch_failed")
            if not self._wait(lambda: self._ui.main_window_present(), self._ready_wait_s):
                self.session.status = "failed"
                return allowlisted(False, "failed", "launch_failed")
        elif not self._ui.main_window_present():
            if not self._launcher.activate() or not self._ui.main_window_present():
                self.session.status = "failed"
                return allowlisted(False, "failed", "launch_failed")

        if mode == "new":
            if not self._ui.invoke_new_task():
                self.session.status = "failed"
                return allowlisted(False, "failed", "fresh_task_failed")
            self.session.created_fresh_task = True
        elif not self._ui.main_window_present():
            self.session.status = "failed"
            return allowlisted(False, "failed", "launch_failed")

        if not self._ui.invoke_voice_start():
            self.session.status = "failed"
            return allowlisted(False, "failed", "voice_start_failed")
        if not self._wait(self._ui.voice_ready, self._ready_wait_s):
            self.session.status = "failed"
            return allowlisted(False, "failed", "voice_not_ready")
        if not self._ui.select_cable_mic():
            self._ui.invoke_voice_stop()
            self._wait(lambda: not self._ui.voice_ready(), self._stop_wait_s)
            self.session.owned = False
            self.session.status = "failed"
            return allowlisted(False, "failed", "cable_mic_not_selected")

        self.session.owned = True
        self.session.status = "ready"
        return allowlisted(True, "ready")

    def stop(self) -> dict[str, Any]:
        if self.session.status == "inactive" and not self.session.owned:
            return allowlisted(True, "inactive")
        self.session.status = "stopping"
        if self._ui.voice_ready() or self.session.owned:
            if not self._ui.invoke_voice_stop():
                self.session.status = "failed"
                return allowlisted(False, "failed", "stop_failed")
            if not self._wait(lambda: not self._ui.voice_ready(), self._stop_wait_s):
                self.session.status = "failed"
                return allowlisted(False, "failed", "stop_failed")
        self.session.owned = False
        self.session.status = "inactive"
        return allowlisted(True, "inactive")

    def _wait(self, predicate: Callable[[], bool], budget: float) -> bool:
        deadline = time.monotonic() + budget
        while time.monotonic() < deadline:
            if predicate():
                return True
            self._sleep(min(0.2, max(0.0, deadline - time.monotonic())))
        return predicate()


class StaticGuard:
    def __init__(self, windows: bool = True, unlocked: bool = True) -> None:
        self.windows = windows
        self.unlocked = unlocked

    def is_windows(self) -> bool:
        return self.windows

    def is_interactive_unlocked(self) -> bool:
        return self.unlocked


class StaticLauncher:
    def __init__(self, present: bool = True, activate_ok: bool = True) -> None:
        self.present = present
        self.activate_ok = activate_ok
        self.activate_calls = 0

    def desktop_present(self) -> bool:
        return self.present

    def activate(self) -> bool:
        self.activate_calls += 1
        if self.activate_ok:
            self.present = True
        return self.activate_ok


class StaticUi:
    def __init__(
        self,
        *,
        window: bool = True,
        unowned_voice: bool = False,
        new_task: bool = True,
        voice_start: bool = True,
        ready_after_start: bool = True,
        voice_stop: bool = True,
        select_ok: bool = True,
    ) -> None:
        self.window = window
        self.unowned_voice = unowned_voice
        self.new_task = new_task
        self.voice_start = voice_start
        self.ready_after_start = ready_after_start
        self.voice_stop = voice_stop
        self.select_ok = select_ok
        self.voice_is_ready = False
        self.new_task_calls = 0
        self.select_calls = 0
        self.voice_stop_calls = 0
        self.close_task_calls = 0
        self.kill_calls = 0

    def main_window_present(self) -> bool:
        return self.window

    def unowned_voice_active(self) -> bool:
        return self.unowned_voice and not self.voice_is_ready

    def invoke_new_task(self) -> bool:
        self.new_task_calls += 1
        return self.new_task

    def invoke_voice_start(self) -> bool:
        if not self.voice_start:
            return False
        self.voice_is_ready = self.ready_after_start
        return True

    def voice_ready(self) -> bool:
        return self.voice_is_ready

    def invoke_voice_stop(self) -> bool:
        self.voice_stop_calls += 1
        if not self.voice_stop:
            return False
        self.voice_is_ready = False
        return True

    def select_cable_mic(self) -> bool:
        self.select_calls += 1
        if not self.voice_is_ready or not self.select_ok:
            return False
        return True

    def close_or_delete_task(self) -> None:
        self.close_task_calls += 1

    def kill_codex(self) -> None:
        self.kill_calls += 1


class StaticCable:
    def __init__(self, present: bool = True) -> None:
        self.present = present

    def output_present(self) -> bool:
        return self.present


class WinSessionGuard:
    def is_windows(self) -> bool:
        return os.name == "nt"

    def is_interactive_unlocked(self) -> bool:
        if os.name != "nt":
            return False
        queried = query_wts_session()
        if queried is None:
            return False
        connect, lock, process_session_id = queried
        return classify_wts_session(connect, lock, process_session_id, _wts_contract()) == "active-unlocked"


class WinPackageLauncher:
    def desktop_present(self) -> bool:
        return bool(_chatgpt_process_ids())

    def activate(self) -> bool:
        if os.name != "nt":
            return False
        aumid = _codex_aumid()
        if not aumid:
            return False
        return _activate_packaged(aumid)


class WinCableMic:
    def output_present(self) -> bool:
        try:
            import soundcard as sc
        except ImportError:
            return False
        needle = CABLE_MIC_NAME.lower()
        for mic in sc.all_microphones(include_loopback=False):
            name = str(getattr(mic, "name", "")).lower()
            if name == needle or ("cable output" in name and "vb-audio" in name):
                return True
        return False


class WinDesktopUi:
    """Semantic UIA adapter scoped to one current-session Codex window."""

    def main_window_present(self) -> bool:
        return _unique_codex_hwnd() is not None

    def unowned_voice_active(self) -> bool:
        return _scoped_name_present(VOICE_READY_NAMES)

    def invoke_new_task(self) -> bool:
        return _scoped_invoke_named(NEW_TASK_NAMES)

    def invoke_voice_start(self) -> bool:
        return _scoped_invoke_named(VOICE_START_NAMES)

    def voice_ready(self) -> bool:
        return _scoped_name_present(VOICE_READY_NAMES)

    def invoke_voice_stop(self) -> bool:
        return _scoped_invoke_named(VOICE_STOP_NAMES)

    def select_cable_mic(self) -> bool:
        if _scoped_selected_name(CABLE_MIC_NAME):
            return True
        if not _scoped_invoke_named(MIC_OPEN_NAMES):
            return False
        if not _scoped_select_named((CABLE_MIC_NAME,)):
            return False
        return _scoped_selected_name(CABLE_MIC_NAME)

    def close_or_delete_task(self) -> None:
        return None

    def kill_codex(self) -> None:
        return None


def query_wts_session() -> tuple[WtsConnect, WtsLock, int] | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import POINTER, byref, c_void_p, wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    wtsapi = ctypes.WinDLL("wtsapi32", use_last_error=True)
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD
    kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, POINTER(wintypes.DWORD)]
    kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
    wtsapi.WTSQuerySessionInformationW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.c_int,
        POINTER(c_void_p),
        POINTER(wintypes.DWORD),
    ]
    wtsapi.WTSQuerySessionInformationW.restype = wintypes.BOOL
    wtsapi.WTSFreeMemory.argtypes = [c_void_p]
    process_session = wintypes.DWORD()
    kernel32.SetLastError(0)
    if not kernel32.ProcessIdToSessionId(kernel32.GetCurrentProcessId(), byref(process_session)):
        return None
    sid = int(process_session.value)

    def _query(info_class: int, min_bytes: int) -> tuple[bool, int, c_void_p]:
        buf = c_void_p()
        nbytes = wintypes.DWORD()
        kernel32.SetLastError(0)
        ok = bool(wtsapi.WTSQuerySessionInformationW(None, sid, info_class, byref(buf), byref(nbytes)))
        return ok, int(nbytes.value), buf

    connect_buf = c_void_p()
    lock_buf = c_void_p()
    try:
        connect_ok, connect_bytes, connect_buf = _query(WTS_CONNECTSTATE, CONNECT_MIN_BYTES)
        connect = WtsConnect(ok=False, bytes_returned=connect_bytes, session_id=None, session_state=None)
        if connect_ok and connect_buf.value and connect_bytes >= CONNECT_MIN_BYTES:
            connect = WtsConnect(
                ok=True,
                bytes_returned=connect_bytes,
                session_id=sid,
                session_state=int(ctypes.c_int.from_address(connect_buf.value).value),
            )
        lock_ok, lock_bytes, lock_buf = _query(WTS_SESSION_INFO_EX, LOCK_MIN_BYTES)
        lock = WtsLock(
            ok=False,
            bytes_returned=lock_bytes,
            level=None,
            session_id=None,
            session_state=None,
            session_flags=None,
        )
        if lock_ok and lock_buf.value and lock_bytes >= LOCK_MIN_BYTES:
            raw = (ctypes.c_ubyte * lock_bytes).from_address(lock_buf.value)
            blob = bytes(raw)
            lock = WtsLock(
                ok=True,
                bytes_returned=lock_bytes,
                level=int.from_bytes(blob[0:4], "little"),
                session_id=int.from_bytes(blob[8:12], "little"),
                session_state=int.from_bytes(blob[12:16], "little", signed=True),
                session_flags=int.from_bytes(blob[16:20], "little", signed=True),
            )
        return connect, lock, sid
    finally:
        if connect_buf.value:
            wtsapi.WTSFreeMemory(connect_buf)
            connect_buf.value = None
        if lock_buf.value:
            wtsapi.WTSFreeMemory(lock_buf)
            lock_buf.value = None


def _wts_contract() -> str:
    if os.name != "nt":
        return "unknown"
    ver = sys.getwindowsversion()
    if ver.major >= 10:
        return "modern"
    return "unknown"


def _chatgpt_process_ids() -> set[int]:
    if os.name != "nt":
        return set()
    import ctypes
    from ctypes import wintypes

    ids: set[int] = set()
    TH32CS_SNAPPROCESS = 0x2

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return ids
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return ids
        while True:
            if entry.szExeFile.lower() == MAIN_UI_PROCESS:
                ids.add(int(entry.th32ProcessID))
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return ids
    finally:
        kernel32.CloseHandle(snapshot)


def _unique_codex_hwnd() -> int | None:
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD
    kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
    found: list[int] = []
    self_session = wintypes.DWORD()
    if not kernel32.ProcessIdToSessionId(kernel32.GetCurrentProcessId(), ctypes.byref(self_session)):
        return None
    pids = _chatgpt_process_ids()
    if not pids:
        return None
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    def _cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, 4):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) not in pids:
            return True
        proc_session = wintypes.DWORD()
        if not kernel32.ProcessIdToSessionId(pid.value, ctypes.byref(proc_session)):
            return True
        if int(proc_session.value) != int(self_session.value):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if not (buf.value or "").startswith(CHROMIUM_CLASS_PREFIX):
            return True
        found.append(int(hwnd))
        return True

    callback = EnumWindowsProc(_cb)
    user32.EnumWindows(callback, 0)
    if len(found) != 1:
        return None
    return found[0]


def _codex_aumid() -> str | None:
    import subprocess

    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-AppxPackage -Name OpenAI.Codex).PackageFamilyName",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except OSError:
        return None
    family = (completed.stdout or "").strip().splitlines()
    if not family:
        return None
    name = family[-1].strip()
    if not name or " " in name:
        return None
    return f"{name}!App"


def _activate_packaged(aumid: str) -> bool:
    import ctypes
    from ctypes import POINTER, byref, c_void_p, c_wchar_p, c_long
    from ctypes import wintypes

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    CLSCTX_LOCAL_SERVER = 0x4
    COINIT_APARTMENTTHREADED = 0x2
    ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
    clsid = _guid("45BA127D-10A8-46EA-8AB7-56EA9078943C")
    iid = _guid("2E941141-7F97-4756-BA1D-9DECDE894A3D")
    obj = c_void_p()
    hr = ole32.CoCreateInstance(byref(clsid), None, CLSCTX_LOCAL_SERVER, byref(iid), byref(obj))
    if hr != 0 or not obj.value:
        return False
    activate_fn = ctypes.WINFUNCTYPE(
        c_long, c_void_p, c_wchar_p, c_wchar_p, wintypes.DWORD, POINTER(wintypes.DWORD)
    )
    vtable = ctypes.cast(obj, POINTER(POINTER(c_void_p))).contents
    fn = activate_fn(vtable[3])
    pid = wintypes.DWORD()
    hr = fn(obj, aumid, "", 0, byref(pid))
    return hr == 0


def _guid(text: str):
    import ctypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    ole32 = ctypes.WinDLL("ole32")
    guid = GUID()
    ole32.CLSIDFromString(ctypes.c_wchar_p("{" + text + "}"), ctypes.byref(guid))
    return guid


def _load_uia():
    try:
        import comtypes.client
        from comtypes.gen.UIAutomationClient import (  # type: ignore
            CUIAutomation,
            IUIAutomation,
            IUIAutomationInvokePattern,
            IUIAutomationSelectionItemPattern,
            TreeScope_Descendants,
            UIA_InvokePatternId,
            UIA_IsEnabledPropertyId,
            UIA_NamePropertyId,
            UIA_SelectionItemPatternId,
        )
    except (ImportError, OSError, ValueError):
        try:
            import comtypes.client

            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import (  # type: ignore
                CUIAutomation,
                IUIAutomation,
                IUIAutomationInvokePattern,
                IUIAutomationSelectionItemPattern,
                TreeScope_Descendants,
                UIA_InvokePatternId,
                UIA_IsEnabledPropertyId,
                UIA_NamePropertyId,
                UIA_SelectionItemPatternId,
            )
        except (ImportError, OSError, ValueError):
            return None
    try:
        uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
    except OSError:
        return None
    return {
        "uia": uia,
        "TreeScope_Descendants": TreeScope_Descendants,
        "UIA_NamePropertyId": UIA_NamePropertyId,
        "UIA_IsEnabledPropertyId": UIA_IsEnabledPropertyId,
        "UIA_InvokePatternId": UIA_InvokePatternId,
        "UIA_SelectionItemPatternId": UIA_SelectionItemPatternId,
        "IUIAutomationInvokePattern": IUIAutomationInvokePattern,
        "IUIAutomationSelectionItemPattern": IUIAutomationSelectionItemPattern,
    }


def _scoped_root():
    packed = _load_uia()
    hwnd = _unique_codex_hwnd()
    if packed is None or hwnd is None:
        return None
    try:
        root = packed["uia"].ElementFromHandle(hwnd)
    except OSError:
        return None
    if not root:
        return None
    packed["root"] = root
    return packed


def _scoped_enabled(names: tuple[str, ...]):
    packed = _scoped_root()
    if packed is None:
        return []
    uia = packed["uia"]
    root = packed["root"]
    found = []
    for name in names:
        condition = uia.CreatePropertyCondition(packed["UIA_NamePropertyId"], name)
        matches = root.FindAll(packed["TreeScope_Descendants"], condition)
        count = int(matches.Length)
        for index in range(count):
            element = matches.GetElement(index)
            try:
                enabled = bool(element.GetCurrentPropertyValue(packed["UIA_IsEnabledPropertyId"]))
            except (OSError, AttributeError, ValueError, TypeError):
                enabled = False
            found.append({"element": element, "enabled": enabled, "in_scope": True, "name": name})
    return found


def _unique_scoped(names: tuple[str, ...]):
    picked = pick_unique_enabled(_scoped_enabled(names))
    if picked is None:
        return None
    return picked["element"]


def _scoped_invoke_named(names: tuple[str, ...]) -> bool:
    packed = _load_uia()
    element = _unique_scoped(names)
    if packed is None or element is None:
        return False
    try:
        pattern = element.GetCurrentPattern(packed["UIA_InvokePatternId"])
        invoke = pattern.QueryInterface(packed["IUIAutomationInvokePattern"])
        invoke.Invoke()
        return True
    except (OSError, AttributeError, ValueError, TypeError):
        return False


def _scoped_name_present(names: tuple[str, ...]) -> bool:
    return _unique_scoped(names) is not None


def _scoped_select_named(names: tuple[str, ...]) -> bool:
    packed = _load_uia()
    element = _unique_scoped(names)
    if packed is None or element is None:
        return False
    try:
        pattern = element.GetCurrentPattern(packed["UIA_SelectionItemPatternId"])
        item = pattern.QueryInterface(packed["IUIAutomationSelectionItemPattern"])
        item.Select()
        return True
    except (OSError, AttributeError, ValueError, TypeError):
        return _scoped_invoke_named(names)


def _scoped_selected_name(name: str) -> bool:
    packed = _load_uia()
    element = _unique_scoped((name,))
    if packed is None or element is None:
        return False
    try:
        pattern = element.GetCurrentPattern(packed["UIA_SelectionItemPatternId"])
        item = pattern.QueryInterface(packed["IUIAutomationSelectionItemPattern"])
        return bool(item.CurrentIsSelected)
    except (OSError, AttributeError, ValueError, TypeError):
        return False


_CONTROLLER: CodexVoiceController | None = None


def build_windows_controller() -> CodexVoiceController:
    return CodexVoiceController(
        guard=WinSessionGuard(),
        launcher=WinPackageLauncher(),
        ui=WinDesktopUi(),
        cable=WinCableMic(),
    )


def default_controller() -> CodexVoiceController:
    global _CONTROLLER
    if _CONTROLLER is None:
        _CONTROLLER = build_windows_controller()
    return _CONTROLLER


def set_controller(controller: CodexVoiceController | None) -> None:
    global _CONTROLLER
    _CONTROLLER = controller


def dumps_result(result: dict[str, Any]) -> str:
    return json.dumps(allowlisted(result.get("ok", False), result.get("status", "failed"), result.get("error")), ensure_ascii=False)
