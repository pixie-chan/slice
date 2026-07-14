"""TLS fingerprint helpers — JA3/JA4 matching via CDP headers.

Note: The actual TLS fingerprint (JA3/JA4) is determined by Chrome's network stack
and can't be changed from JS. What we CAN do via CDP is:
1. Set consistent headers that match our fingerprint profile
2. Ensure Accept-Language, User-Agent, and Client Hints are aligned
3. Use Network.setExtraHTTPHeaders for custom header ordering

The TLS handshake itself is controlled by the browser binary.
Chromium's built-in TLS stack has a distinct JA3 fingerprint that is
generally trusted by bot detection systems.
"""


def get_extra_headers(profile: dict = None) -> dict:
    """Build extra HTTP headers to align with fingerprint profile."""
    if profile is None:
        profile = {}

    headers = {}
    languages = profile.get("languages", ["en-US", "en"])
    headers["Accept-Language"] = ",".join(languages) + ";q=0.9"

    # Sec-CH-UA headers are set via Network.setUserAgentOverride, not here.
    # These extra headers supplement that.
    headers["sec-ch-ua-full-version-list"] = ""  # Will be set by CDP metadata
    headers["Upgrade-Insecure-Requests"] = "1"
    headers["sec-fetch-site"] = "none"
    headers["sec-fetch-mode"] = "navigate"
    headers["sec-fetch-user"] = "?1"
    headers["sec-fetch-dest"] = "document"

    return headers
