"""Browser lifecycle management — launch Chrome, connect via CDP, manage tabs."""

import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
from typing import Optional
from urllib.request import urlopen

from .connection import CDPConnection

logger = logging.getLogger(__name__)

# Chrome launch arguments for stealth headless browsing
CHROME_ARGS = [
    "--remote-debugging-port=0",
    "--remote-allow-origins=*",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-extensions",
    "--use-gl=swiftshader",
    "--disable-hang-monitor",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-sync",
    "--disable-translate",
    "--metrics-recording-only",
    "--no-sandbox",
    "--headless=new",
    "--window-size=1920,1080",
    "--disable-blink-features=AutomationControlled",
    # Additional anti-detection hardening
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-features=ImprovedCookieControls,LazyFrameLoading,GlobalMediaControls,DestroyProfileOnBrowserClose,MediaRouter,DialMediaRouteProvider,AcceptCHFrame,AutoExpandDetailsElement,CertificateTransparencyComponentUpdater,AvoidUnnecessaryBeforeUnloadCheckSync,Translate",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--disable-ipc-flooding-protection",
    "--disable-component-extensions-with-background-pages",
    "--disable-breakpad",
    "--disable-crash-reporter",
    "--disable-component-update",
    "--disable-domain-reliability",
    "--disable-features=AudioServiceOutOfProcess",
    "--disable-field-trial-config",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--enable-features=SharedArrayBuffer",
    # Prevent Chrome from adding "Chrome is being controlled by automated software" banner
    "--disable-blink-features=AutomationControlled",
    "--force-color-profile=srgb",
    "--disable-features=BlockInsecurePrivateNetworkRequests,PrivateNetworkAccessSendPreflights",
]


def _find_chrome() -> str:
    """Find Chrome or Chromium binary on the system."""
    # First: check Playwright's bundled Chromium (most reliable on this system)
    import glob as _glob

    playwright_glob = os.path.expanduser(
        "~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"
    )
    playwright_hits = sorted(_glob.glob(playwright_glob), reverse=True)
    for path in playwright_hits:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            logger.info(f"Found Playwright Chromium: {path}")
            return path

    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/opt/google/chrome/chrome",
        "/snap/bin/chromium",
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError(
        "Chrome/Chromium not found. Install google-chrome or chromium."
    )


class Browser:
    """Controls a Chrome browser process via raw CDP."""

    def __init__(
        self,
        process: subprocess.Popen,
        debug_port: int,
        ws_url: str,
        connection: CDPConnection,
    ):
        self._process = process
        self._debug_port = debug_port
        self._ws_url = ws_url
        self._connection = connection
        self._tabs: dict[str, "Tab"] = {}
        self._browser_contexts: list[str] = []

    @classmethod
    async def launch(
        cls,
        chrome_path: Optional[str] = None,
        extra_args: Optional[list[str]] = None,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> "Browser":
        """Launch Chrome and connect via CDP.

        Args:
            chrome_path: Path to Chrome binary (auto-detected if None)
            extra_args: Additional Chrome command-line arguments
            headless: Run in headless mode
            user_data_dir: Chrome user data directory (temp dir if None)
            proxy: Proxy server URL (e.g., "socks5://host:port")

        Returns:
            Browser instance ready for automation.
        """
        if chrome_path is None:
            chrome_path = _find_chrome()

        args = [chrome_path]
        args.extend(CHROME_ARGS)

        if not headless:
            args = [a for a in args if not a.startswith("--headless")]
            args.append("--window-size=1920,1080")

        if user_data_dir:
            args.append(f"--user-data-dir={user_data_dir}")

        if proxy:
            args.append(f"--proxy-server={proxy}")

        if extra_args:
            args.extend(extra_args)

        logger.info(f"Launching Chrome: {' '.join(args)}")

        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
        )

        # Wait for Chrome to output its WebSocket URL
        ws_url = await _wait_for_ws_url(process, timeout=15.0)

        # Extract the debug port from the WS URL
        # Format: ws://127.0.0.1:{port}/devtools/browser/{guid}
        port = int(ws_url.split(":")[2].split("/")[0])

        # Connect to the browser-level WebSocket
        connection = CDPConnection(ws_url)
        await connection.connect()

        browser = cls(process, port, ws_url, connection)
        logger.info(f"Chrome launched on port {port}, connected at {ws_url}")
        return browser

    @property
    def connection(self) -> CDPConnection:
        return self._connection

    async def get_version(self) -> dict:
        """Get browser version info."""
        return await self._connection.send("Browser.getVersion")

    async def new_tab(self, url: str = "about:blank") -> "Tab":
        """Create a new tab and return a Tab object."""
        result = await self._connection.send(
            "Target.createTarget", {"url": url}
        )
        target_id = result["targetId"]

        # Attach to the target to get a session
        attach_result = await self._connection.send(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )
        session_id = attach_result["sessionId"]

        # Enable auto-attach for future targets
        await self._connection.send(
            "Target.setAutoAttach",
            {
                "autoAttach": True,
                "waitForDebuggerOnStart": False,
                "flatten": True,
            },
        )

        tab = Tab(self._connection, target_id, session_id)
        self._tabs[target_id] = tab
        return tab

    async def get_targets(self) -> list[dict]:
        """List all targets (tabs, iframes, workers)."""
        result = await self._connection.send("Target.getTargets")
        return result.get("targetInfos", [])

    async def close_tab(self, target_id: str) -> None:
        """Close a tab by target ID."""
        await self._connection.send(
            "Target.closeTarget", {"targetId": target_id}
        )
        self._tabs.pop(target_id, None)

    async def close(self) -> None:
        """Gracefully shut down the browser."""
        try:
            await self._connection.send("Browser.close", timeout=5.0)
        except Exception:
            logger.debug("Browser.close command failed, killing process")

        await self._connection.disconnect()

        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

        logger.info("Browser closed")


class Tab:
    """Represents a browser tab with its own CDP session."""

    def __init__(
        self, browser_conn: CDPConnection, target_id: str, session_id: str
    ):
        self._conn = browser_conn
        self.target_id = target_id
        self.session_id = session_id

    async def send(self, method: str, params: Optional[dict] = None, timeout: float = 30.0):
        """Send a CDP command to this tab's session."""
        return await self._conn.send(method, params, session_id=self.session_id, timeout=timeout)

    async def navigate(self, url: str, wait_event: str = "Page.loadEventFired", timeout: float = 30.0) -> None:
        """Navigate to a URL and wait for load."""
        await self.send("Page.enable")
        load_future: asyncio.Future = asyncio.get_event_loop().create_future()

        async def on_load(_params):
            if not load_future.done():
                load_future.set_result(True)

        self._conn.on(wait_event, on_load)

        try:
            await self.send("Page.navigate", {"url": url})
            await asyncio.wait_for(load_future, timeout=timeout)
        finally:
            self._conn.off(wait_event, on_load)

    async def evaluate(self, expression: str, return_by_value: bool = True) -> any:
        """Evaluate JavaScript in the tab."""
        result = await self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": return_by_value,
                "awaitPromise": True,
            },
        )
        remote_obj = result.get("result", {})
        if "value" in remote_obj:
            return remote_obj["value"]
        if remote_obj.get("type") == "undefined":
            return None
        if remote_obj.get("subtype") == "error":
            raise RuntimeError(f"JS error: {remote_obj.get('description', 'unknown')}")
        return remote_obj

    async def add_script(self, script: str, run_at: str = "document_start", world_name: str = None) -> str:
        """Inject a script that runs before every page load.

        Args:
            script: JS source code to inject
            run_at: When to run ("document_start" or "document_end")
            world_name: Named execution world for isolation (e.g. "__slice_stealth__")

        Returns:
            Script identifier for later removal.
        """
        params = {"source": script, "runAt": run_at}
        if world_name:
            params["worldName"] = world_name
        result = await self.send(
            "Page.addScriptToEvaluateOnNewDocument",
            params,
        )
        return result["identifier"]

    async def remove_script(self, identifier: str) -> None:
        """Remove a previously injected script."""
        await self.send(
            "Page.removeScriptToEvaluateOnNewDocument",
            {"identifier": identifier},
        )

    async def get_url(self) -> str:
        """Get the current URL of the tab."""
        result = await self.send("Runtime.evaluate", {"expression": "window.location.href"})
        return result.get("result", {}).get("value", "")

    async def get_document(self) -> dict:
        """Get the root DOM node."""
        result = await self.send("DOM.getDocument")
        return result

    async def query_selector(self, selector: str) -> Optional[int]:
        """Query for a single element, return nodeId."""
        doc = await self.get_document()
        try:
            result = await self.send(
                "DOM.querySelector",
                {"nodeId": doc["root"]["nodeId"], "selector": selector},
            )
            node_id = result.get("nodeId", 0)
            return node_id if node_id else None
        except Exception:
            return None

    async def screenshot(self, format: str = "png", quality: int = 80) -> bytes:
        """Take a screenshot of the tab, returns raw image bytes."""
        import base64

        result = await self.send(
            "Page.captureScreenshot",
            {"format": format, "quality": quality, "captureBeyondViewport": True},
        )
        return base64.b64decode(result["data"])

    async def close(self) -> None:
        """Close this tab."""
        await self._conn.send(
            "Target.closeTarget", {"targetId": self.target_id}
        )


async def _wait_for_ws_url(process: subprocess.Popen, timeout: float = 15.0) -> str:
    """Wait for Chrome to print its DevTools WebSocket URL to stderr.

    Chrome outputs something like:
        DevTools listening on ws://127.0.0.1:9222/devtools/browser/abc123
    """
    import time

    deadline = time.monotonic() + timeout
    buffer = b""

    # Set stderr to non-blocking
    import fcntl

    fd = process.stderr.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    while time.monotonic() < deadline:
        try:
            chunk = os.read(fd, 4096)
            buffer += chunk
            text = buffer.decode("utf-8", errors="replace")
            for line in text.split("\n"):
                if "DevTools listening on" in line:
                    ws_url = line.split("ws://")[1].strip()
                    return f"ws://{ws_url}"
        except (BlockingIOError, OSError):
            pass

        if process.poll() is not None:
            stderr_out = buffer.decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Chrome exited with code {process.returncode}.\nStderr:\n{stderr_out}"
            )

        await asyncio.sleep(0.1)

    raise TimeoutError(f"Chrome did not output WebSocket URL within {timeout}s")
