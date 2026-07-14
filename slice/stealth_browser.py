"""High-level StealthBrowser — launches Chrome with all stealth protections."""

import logging
from typing import Optional

from .browser import Browser, Tab
from .stealth.apply import apply_stealth, build_stealth_script

logger = logging.getLogger(__name__)


class StealthBrowser:
    """A stealth browser instance with all anti-detection measures applied."""

    def __init__(self, browser: Browser, profile: dict = None):
        self._browser = browser
        self._profile = profile or {}
        self._base_script = build_stealth_script(profile)

    @classmethod
    async def launch(
        cls,
        profile: dict = None,
        chrome_path: str = None,
        headless: bool = True,
        proxy: str = None,
        extra_args: list[str] = None,
    ) -> "StealthBrowser":
        """Launch Chrome with stealth protections.

        Args:
            profile: Fingerprint profile (from fingerprint.generator)
            chrome_path: Path to Chrome binary
            headless: Run in headless mode
            proxy: Proxy server URL
            extra_args: Extra Chrome args

        Returns:
            StealthBrowser instance ready for automation.
        """
        browser = await Browser.launch(
            chrome_path=chrome_path,
            headless=headless,
            proxy=proxy,
            extra_args=extra_args,
        )
        return cls(browser, profile)

    @property
    def browser(self) -> Browser:
        return self._browser

    @property
    def profile(self) -> dict:
        return self._profile

    async def new_page(self, url: str = "about:blank") -> "StealthPage":
        """Create a new stealth-protected tab.

        Always creates at about:blank first, applies stealth, then navigates
        so that addScriptToEvaluateOnNewDocument runs before page JS.
        """
        tab = await self._browser.new_tab("about:blank")
        # Apply stealth BEFORE navigating to target URL
        await apply_stealth(tab, self._profile)
        if url != "about:blank":
            await tab.navigate(url)
        return StealthPage(tab, self._profile)

    async def close(self) -> None:
        """Shut down the browser."""
        await self._browser.close()


class StealthPage:
    """A browser tab with stealth protections applied."""

    def __init__(self, tab: Tab, profile: dict = None):
        self._tab = tab
        self._profile = profile or {}

    @property
    def tab(self) -> Tab:
        return self._tab

    @property
    def target_id(self) -> str:
        return self._tab.target_id

    @property
    def session_id(self) -> str:
        return self._tab.session_id

    async def goto(self, url: str, timeout: float = 30.0) -> None:
        """Navigate to a URL (re-applies stealth scripts since they persist)."""
        await self._tab.navigate(url, timeout=timeout)

    async def evaluate(self, expression: str):
        """Evaluate JavaScript in the page."""
        return await self._tab.evaluate(expression)

    async def click(self, selector: str) -> None:
        """Click an element using human-like mouse movement."""
        from .stealth.behavior import human_click

        # Get element position
        rect = await self.evaluate(
            f"JSON.stringify(document.querySelector('{selector}').getBoundingClientRect())"
        )
        import json

        if isinstance(rect, str):
            rect = json.loads(rect)
        x = int(rect["x"] + rect["width"] / 2)
        y = int(rect["y"] + rect["height"] / 2)
        await human_click(self._tab._conn, x, y, self._tab.session_id)

    async def type_text(self, text: str) -> None:
        """Type text with human-like delays."""
        from .stealth.behavior import human_type

        await human_type(self._tab._conn, text, self._tab.session_id)

    async def scroll(self, delta_y: int) -> None:
        """Scroll the page with human-like behavior."""
        from .stealth.behavior import human_scroll

        await human_scroll(self._tab._conn, delta_y, session_id=self._tab.session_id)

    async def screenshot(self, format: str = "png") -> bytes:
        """Take a screenshot."""
        return await self._tab.screenshot(format)

    async def get_url(self) -> str:
        return await self._tab.get_url()

    async def wait_for_selector(self, selector: str, timeout: float = 10.0) -> bool:
        """Wait until a selector exists in the DOM."""
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            result = await self.evaluate(
                f"!!document.querySelector('{selector}')"
            )
            if result:
                return True
            await asyncio.sleep(0.2)
        return False

    async def close(self) -> None:
        await self._tab.close()
