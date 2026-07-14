"""Proxy provider integrations — helpers for popular proxy services."""

from urllib.parse import urlparse


def parse_proxy_url(url: str) -> dict:
    """Parse a proxy URL into components.

    Args:
        url: Proxy URL (e.g., "http://user:pass@host:port")

    Returns:
        Dict with 'scheme', 'host', 'port', 'username', 'password'.
    """
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme or "http",
        "host": parsed.hostname or "",
        "port": parsed.port or 8080,
        "username": parsed.username or "",
        "password": parsed.password or "",
    }


def build_brightdata_proxy(
    host: str,
    port: int,
    username: str,
    password: str,
    session_id: str = None,
) -> str:
    """Build a BrightData (formerly Luminati) proxy URL.

    Args:
        host: Proxy host
        port: Proxy port
        username: Zone username
        password: Zone password
        session_id: Optional session ID for sticky sessions

    Returns:
        Proxy URL string.
    """
    user = username
    if session_id:
        user += f"-session-{session_id}"
    return f"http://{user}:{password}@{host}:{port}"


def build_oxylabs_proxy(
    host: str,
    port: int,
    username: str,
    password: str,
    session_id: str = None,
) -> str:
    """Build an Oxylabs proxy URL.

    Args:
        host: Proxy host
        port: Proxy port
        username: Username
        password: Password
        session_id: Optional session for sticky

    Returns:
        Proxy URL string.
    """
    user = username
    if session_id:
        user += f"-sessid-{session_id}"
    return f"http://{user}:{password}@{host}:{port}"


def format_proxy_for_chrome(proxy_url: str) -> str:
    """Convert a full proxy URL (with auth) to Chrome-compatible format.

    Chrome's --proxy-server doesn't support inline credentials.
    Returns just the scheme://host:port part.
    """
    parsed = urlparse(proxy_url)
    port = parsed.port or 8080
    scheme = parsed.scheme or "http"
    return f"{scheme}://{parsed.hostname}:{port}"
