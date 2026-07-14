"""Response modification via CDP Fetch domain.

Note: Response interception requires handleAuthRequests or
Fetch.enable with requestStage: "Response". Use sparingly —
modifying responses is slower than request modification.
"""

import base64
import logging

logger = logging.getLogger(__name__)


class ResponseInterceptor:
    """Intercept and modify HTTP responses.

    Usage:
        ri = ResponseInterceptor(connection, session_id)
        await ri.enable()
        ri.on_url("example.com/api", modify_response_func)
        # ... navigate ...
        await ri.disable()
    """

    def __init__(self, connection, session_id: str = None):
        self._conn = connection
        self._session_id = session_id
        self._enabled = False
        self._response_rules: list[dict] = []

    async def enable(self, patterns: list[dict] = None) -> None:
        """Enable response interception."""
        if patterns is None:
            patterns = [{"urlPattern": "*", "requestStage": "Response"}]

        self._conn.on("Fetch.requestPaused", self._on_response_paused)
        await self._conn.send(
            "Fetch.enable",
            {"patterns": patterns, "handleAuthRequests": False},
            session_id=self._session_id,
        )
        self._enabled = True

    async def disable(self) -> None:
        """Disable response interception."""
        self._conn.off("Fetch.requestPaused", self._on_response_paused)
        await self._conn.send(
            "Fetch.disable", session_id=self._session_id
        )
        self._enabled = False

    def on_url(self, url_pattern: str, modifier_func) -> None:
        """Add a response modifier for URLs matching a pattern.

        Args:
            url_pattern: Substring to match in URL
            modifier_func: async func(response_body: str) -> str (modified body)
        """
        self._response_rules.append({
            "pattern": url_pattern,
            "modifier": modifier_func,
        })

    async def _on_response_paused(self, params: dict) -> None:
        """Handle a paused response."""
        request_id = params.get("requestId", "")
        request = params.get("request", {})
        url = request.get("url", "")

        for rule in self._response_rules:
            if rule["pattern"] in url:
                try:
                    # Get response body
                    body_result = await self._conn.send(
                        "Fetch.getResponseBody",
                        {"requestId": request_id},
                        session_id=self._session_id,
                    )
                    body = body_result.get("body", "")
                    is_base64 = body_result.get("base64Encoded", False)

                    if is_base64:
                        body = base64.b64decode(body).decode("utf-8", errors="replace")

                    # Apply modifier
                    modified = await rule["modifier"](body)

                    # Fulfill with modified response
                    await self._conn.send(
                        "Fetch.fulfillRequest",
                        {
                            "requestId": request_id,
                            "responseCode": params.get("responseStatusCode", 200),
                            "responseHeaders": params.get("responseHeaders", []),
                            "body": base64.b64encode(modified.encode()).decode(),
                        },
                        session_id=self._session_id,
                    )
                    return
                except Exception:
                    logger.exception(f"Error modifying response for {url[:80]}")
                    break

        # No modification, continue
        await self._conn.send(
            "Fetch.continueResponse",
            {"requestId": request_id},
            session_id=self._session_id,
        )
