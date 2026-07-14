"""Request interception and modification via CDP Fetch.enable.

Intercepts requests in-flight to add/modify headers matching
the fingerprint profile, block resources, or modify responses.
"""

import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class RequestInterceptor:
    """Intercepts and modifies network requests using CDP Fetch domain.

    Usage:
        interceptor = RequestInterceptor(connection, session_id)
        await interceptor.enable(profile=profile)
        # ... navigate pages ...
        await interceptor.disable()
    """

    def __init__(self, connection, session_id: str = None):
        self._conn = connection
        self._session_id = session_id
        self._enabled = False
        self._custom_headers: dict[str, str] = {}
        self._blocked_urls: list[str] = []
        self._request_modifiers: list[Callable] = []

    async def enable(
        self,
        profile: dict = None,
        patterns: list[dict] = None,
    ) -> None:
        """Enable request interception.

        Args:
            profile: Fingerprint profile to align headers with
            patterns: Custom Fetch.enable patterns (default: intercept all requests)
        """
        if patterns is None:
            patterns = [{"urlPattern": "*", "requestStage": "Request"}]

        # Set up custom headers from profile
        if profile:
            self._setup_profile_headers(profile)

        # Register the event handler
        self._conn.on("Fetch.requestPaused", self._on_request_paused)

        # Enable Fetch domain
        await self._conn.send(
            "Fetch.enable",
            {"patterns": patterns, "handleAuthRequests": False},
            session_id=self._session_id,
        )
        self._enabled = True
        logger.info("Request interception enabled")

    async def disable(self) -> None:
        """Disable request interception."""
        self._conn.off("Fetch.requestPaused", self._on_request_paused)
        await self._conn.send(
            "Fetch.disable", session_id=self._session_id
        )
        self._enabled = False
        logger.info("Request interception disabled")

    def add_header(self, name: str, value: str) -> None:
        """Add a custom header to all intercepted requests."""
        self._custom_headers[name] = value

    def block_url(self, pattern: str) -> None:
        """Block requests matching a URL pattern.

        Args:
            pattern: Simple string match (if pattern in url, block it)
        """
        self._blocked_urls.append(pattern)

    def add_request_modifier(self, modifier: Callable) -> None:
        """Add a custom request modifier function.

        The modifier receives (request_id, request_info) and returns
        modified params dict or None to continue without changes.
        """
        self._request_modifiers.append(modifier)

    def _setup_profile_headers(self, profile: dict) -> None:
        """Set up headers to match fingerprint profile."""
        langs = profile.get("languages", ["en-US", "en"])
        self._custom_headers["Accept-Language"] = ",".join(langs) + ";q=0.9"

    async def _on_request_paused(self, params: dict) -> None:
        """Handle a paused request — modify headers and continue or block."""
        request_id = params.get("requestId", "")
        request = params.get("request", {})
        url = request.get("url", "")

        # Check if URL should be blocked
        for pattern in self._blocked_urls:
            if pattern in url:
                logger.debug(f"Blocked request: {url[:80]}")
                await self._conn.send(
                    "Fetch.failRequest",
                    {"requestId": request_id, "reason": "BlockedByClient"},
                    session_id=self._session_id,
                )
                return

        # Run custom modifiers
        for modifier in self._request_modifiers:
            try:
                result = modifier(request_id, request)
                if asyncio.iscoroutine(result):
                    result = await result
                if result:
                    await self._conn.send(
                        "Fetch.continueRequest",
                        {"requestId": request_id, **result},
                        session_id=self._session_id,
                    )
                    return
            except Exception:
                logger.exception("Error in request modifier")

        # Apply custom headers
        if self._custom_headers:
            headers = request.get("headers", {})
            headers.update(self._custom_headers)

            # Convert to CDP header format (list of name/value pairs)
            header_list = [
                {"name": k, "value": v} for k, v in headers.items()
            ]
            await self._conn.send(
                "Fetch.continueRequest",
                {
                    "requestId": request_id,
                    "headers": header_list,
                },
                session_id=self._session_id,
            )
        else:
            # No modifications needed, continue as-is
            await self._conn.send(
                "Fetch.continueRequest",
                {"requestId": request_id},
                session_id=self._session_id,
            )
