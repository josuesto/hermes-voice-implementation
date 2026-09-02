"""Owned loopback HTTP host for the bundled browser-call runtime.

Imported only when browser transport starts. Missing aiohttp or aiortc must
not prevent the Hermes plugin or physical-mic transport from loading.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

BROWSER_HOST = "127.0.0.1"
BROWSER_PORT = 8765
BROWSER_URL = f"http://{BROWSER_HOST}:{BROWSER_PORT}/"
STARTUP_TIMEOUT_S = 8.0
STOP_TIMEOUT_S = 8.0


class OwnedBrowserHost:
    """Bind 127.0.0.1 in an owned thread and stop the exact owned server."""

    def __init__(self, host: str = BROWSER_HOST, port: int = BROWSER_PORT) -> None:
        if host not in ("127.0.0.1", "::1", "localhost"):
            raise ValueError("this slice binds to loopback only")
        self._host = host
        self._port = int(port)
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._runner: Any = None
        self._call_server: Any = None
        self._ready = threading.Event()
        self._last_error: str | None = None

    def url(self) -> str:
        return f"http://{self._host}:{self._port}/"

    def error(self) -> str | None:
        return self._last_error

    def diagnostics(self) -> dict[str, str]:
        call_server = self._call_server
        if call_server is None or not self.is_running():
            return {
                "peer": "none",
                "browser_audio": "no-peer",
                "cable": "inactive",
            }
        snapshot = call_server.diagnostics()
        return {
            "peer": snapshot.get("peer", "none"),
            "browser_audio": snapshot.get("browser_audio", "no-peer"),
            "cable": snapshot.get("cable", "inactive"),
        }

    def start(self) -> bool:
        if self.is_running():
            return True
        self._last_error = None
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run, name="hermes-voice-browser-host", daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=STARTUP_TIMEOUT_S)
        if not self.is_running():
            if self._last_error is None:
                self._last_error = "browser_start_failed"
            self.stop()
            return False
        return True

    def is_running(self) -> bool:
        thread = self._thread
        return (
            self._last_error is None
            and thread is not None
            and thread.is_alive()
            and self._ready.is_set()
            and self._runner is not None
        )

    def stop(self) -> bool:
        loop = self._loop
        thread = self._thread
        if loop is not None and loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self._shutdown(), loop)
                future.result(timeout=STOP_TIMEOUT_S)
            except Exception:
                self._last_error = self._last_error or "audio_bridge_failed"
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError:
                pass
        if thread is not None:
            thread.join(timeout=STOP_TIMEOUT_S)
        alive = thread is not None and thread.is_alive()
        self._thread = None
        self._loop = None
        self._runner = None
        self._call_server = None
        return not alive

    def _run(self) -> None:
        try:
            import numpy  # noqa: F401
            import sounddevice  # noqa: F401
            from aiohttp import web
            from aiortc import RTCPeerConnection  # noqa: F401
            from av import AudioFrame  # noqa: F401

            from companion.browser_call.server import BrowserCallServer, build_app
        except ImportError:
            self._last_error = "browser_dependency_missing"
            self._ready.set()
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            self._call_server = BrowserCallServer()
            app = build_app(self._call_server)
            runner = web.AppRunner(app)
            loop.run_until_complete(runner.setup())
            site = web.TCPSite(runner, self._host, self._port)
            loop.run_until_complete(site.start())
            self._runner = runner
            self._ready.set()
            loop.run_forever()
        except OSError:
            self._last_error = "browser_start_failed"
            self._ready.set()
            loop.run_until_complete(self._shutdown())
        except Exception:
            self._last_error = "browser_start_failed"
            self._ready.set()
            loop.run_until_complete(self._shutdown())
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
            if self._loop is loop:
                self._loop = None

    async def _shutdown(self) -> None:
        runner, self._runner = self._runner, None
        call_server, self._call_server = self._call_server, None
        if call_server is not None:
            await call_server.close()
        if runner is not None:
            await runner.cleanup()
