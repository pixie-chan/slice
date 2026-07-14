"""Raw CDP (Chrome DevTools Protocol) WebSocket client.

Communicates with Chrome over WebSocket using JSON messages.
No Selenium, no Playwright, no Puppeteer — just raw CDP.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import websockets
import websockets.exceptions

logger = logging.getLogger(__name__)


class CDPConnection:
    """Low-level CDP WebSocket connection to a Chrome instance or tab."""

    def __init__(self, ws_url: str, session_id: Optional[str] = None):
        self.ws_url = ws_url
        self.session_id = session_id
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._cmd_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._event_handlers: dict[str, list[Callable]] = {}
        self._receiver_task: Optional[asyncio.Task] = None
        self._connected = False

    async def connect(self) -> None:
        """Open WebSocket connection and start listening."""
        logger.info(f"Connecting to {self.ws_url}")
        self._ws = await websockets.connect(
            self.ws_url,
            max_size=256 * 1024 * 1024,  # 256MB for large page content
            ping_interval=20,
            ping_timeout=10,
        )
        self._connected = True
        self._receiver_task = asyncio.create_task(self._receive_loop())
        logger.info("Connected")

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        self._connected = False
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None
        # Cancel any pending commands
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()
        logger.info("Disconnected")

    @property
    def connected(self) -> bool:
        return self._connected and self._ws is not None

    async def send(
        self,
        method: str,
        params: Optional[dict] = None,
        session_id: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Any:
        """Send a CDP command and wait for the response.

        Args:
            method: CDP method (e.g., "Page.navigate")
            params: Method parameters
            session_id: Target session ID (for tab-specific commands)
            timeout: Seconds to wait for response

        Returns:
            The 'result' dict from the CDP response.

        Raises:
            CDPError: If the CDP command returns an error.
            asyncio.TimeoutError: If no response within timeout.
        """
        if not self._ws or not self._connected:
            raise ConnectionError("Not connected")

        self._cmd_id += 1
        cmd_id = self._cmd_id
        msg: dict[str, Any] = {"id": cmd_id, "method": method}
        if params:
            msg["params"] = params
        sid = session_id or self.session_id
        if sid:
            msg["sessionId"] = sid

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[cmd_id] = future

        raw = json.dumps(msg)
        logger.debug(f"SEND: {raw[:500]}")
        await self._ws.send(raw)

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(cmd_id, None)
            raise asyncio.TimeoutError(
                f"CDP command timed out after {timeout}s: {method}"
            )

        if "error" in result:
            raise CDPError(result["error"], method)
        return result.get("result", {})

    async def send_no_wait(
        self,
        method: str,
        params: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Fire-and-forget CDP command (no response expected)."""
        if not self._ws or not self._connected:
            raise ConnectionError("Not connected")

        self._cmd_id += 1
        msg: dict[str, Any] = {"id": self._cmd_id, "method": method}
        if params:
            msg["params"] = params
        sid = session_id or self.session_id
        if sid:
            msg["sessionId"] = sid

        await self._ws.send(json.dumps(msg))

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler.

        Args:
            event: CDP event name (e.g., "Network.requestWillBeSent")
            handler: Async callable that receives the event params dict.
        """
        self._event_handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """Remove an event handler."""
        handlers = self._event_handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    async def _receive_loop(self) -> None:
        """Listen for incoming WebSocket messages and dispatch them."""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {raw[:200]}")
                    continue

                logger.debug(f"RECV: {raw[:500]}")

                # Response to a command (has 'id')
                if "id" in msg:
                    cmd_id = msg["id"]
                    future = self._pending.pop(cmd_id, None)
                    if future and not future.done():
                        future.set_result(msg)
                # Event (no 'id', has 'method')
                elif "method" in msg:
                    event = msg["method"]
                    params = msg.get("params", {})
                    handlers = self._event_handlers.get(event, [])
                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(params)
                            else:
                                handler(params)
                        except Exception:
                            logger.exception(f"Error in handler for {event}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self._connected = False
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Unexpected error in receive loop")
            self._connected = False


class CDPError(Exception):
    """Error returned by a CDP command."""

    def __init__(self, error: dict, method: str = ""):
        self.code = error.get("code", -1)
        self.message = error.get("message", "Unknown error")
        self.data = error.get("data")
        self.method = method
        super().__init__(f"CDP error in {method}: [{self.code}] {self.message}")


class CDPSession(CDPConnection):
    """A tab/target session that shares the browser WebSocket but uses sessionId."""

    def __init__(self, browser_ws_url: str, session_id: str):
        super().__init__(browser_ws_url, session_id=session_id)
