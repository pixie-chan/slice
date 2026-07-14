"""Proxy rotation and session management."""

import logging
import random
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages proxy rotation with sticky session support.

    Supports: http://, https://, socks5:// proxy formats.
    """

    def __init__(self, proxies: list[str] = None):
        self.proxies = proxies or []
        self._current_index = 0
        self._domain_sessions: dict[str, str] = {}  # domain -> proxy
        self._health: dict[str, bool] = {p: True for p in self.proxies}

    def add(self, proxy: str) -> None:
        """Add a proxy to the pool."""
        self.proxies.append(proxy)
        self._health[proxy] = True

    def add_many(self, proxies: list[str]) -> None:
        """Add multiple proxies."""
        for p in proxies:
            self.add(p)

    def rotate(self) -> str:
        """Switch to the next healthy proxy in round-robin.

        Returns:
            The selected proxy URL.
        """
        healthy = self._get_healthy()
        if not healthy:
            raise RuntimeError("No healthy proxies available")
        self._current_index = (self._current_index + 1) % len(healthy)
        return healthy[self._current_index]

    def random(self) -> str:
        """Pick a random healthy proxy."""
        healthy = self._get_healthy()
        if not healthy:
            raise RuntimeError("No healthy proxies available")
        return random.choice(healthy)

    def get_for_domain(self, domain: str) -> str:
        """Get a sticky proxy for a domain (same proxy for session persistence).

        If the domain hasn't been seen, assigns the next proxy.
        """
        if domain not in self._domain_sessions:
            self._domain_sessions[domain] = self.rotate()
        return self._domain_sessions[domain]

    def get_chrome_arg(self, proxy: str) -> str:
        """Convert proxy URL to Chrome --proxy-server argument.

        Args:
            proxy: Proxy URL (e.g., "http://user:pass@host:port")

        Returns:
            Chrome proxy argument value.
        """
        parsed = urlparse(proxy)
        # Chrome --proxy-server doesn't support auth in URL
        # Auth is handled via CDP's Fetch.enable or Network.setExtraHTTPHeaders
        host_port = f"{parsed.hostname}:{parsed.port}"
        scheme = parsed.scheme or "http"
        if scheme == "socks5":
            return f"socks5://{host_port}"
        return f"{scheme}://{host_port}"

    def mark_unhealthy(self, proxy: str) -> None:
        """Mark a proxy as unhealthy (e.g., after connection failures)."""
        self._health[proxy] = False
        logger.warning(f"Proxy marked unhealthy: {proxy}")

    def mark_healthy(self, proxy: str) -> None:
        """Mark a proxy as healthy again."""
        self._health[proxy] = True

    def reset_sessions(self) -> None:
        """Clear all domain -> proxy mappings."""
        self._domain_sessions.clear()

    def _get_healthy(self) -> list[str]:
        """Get list of healthy proxies."""
        healthy = [p for p in self.proxies if self._health.get(p, True)]
        if not healthy:
            # Reset all to healthy as fallback
            for p in self._health:
                self._health[p] = True
            return list(self.proxies)
        return healthy
