"""User-Agent, Client Hints, and Accept-Language header alignment."""

# Default Windows Chrome 126 User-Agent
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def make_user_agent_script(user_agent: str = DEFAULT_UA) -> str:
    """Spoof navigator.userAgent."""
    return f"""
Object.defineProperty(Object.getPrototypeOf(navigator), 'userAgent', {{
    get: () => '{user_agent}',
    configurable: true
}});
Object.defineProperty(Object.getPrototypeOf(navigator), 'appVersion', {{
    get: () => '{user_agent.replace("Mozilla/", "")}',
    configurable: true
}});
"""


def make_user_agent_cdp_params(profile: dict = None) -> dict:
    """Build Network.setUserAgentOverride params for CDP.

    This also sets Client Hints (platform, brands, mobile).
    """
    if profile is None:
        profile = {}

    ua = profile.get("user_agent", DEFAULT_UA)
    os_type = profile.get("os", "windows")
    platform = "Windows" if os_type == "windows" else ("macOS" if os_type == "macos" else "Linux")
    browser_version = profile.get("browser_version", "126.0.0.0")
    major = browser_version.split(".")[0]

    params = {
        "userAgent": ua,
        "platform": platform,
        "acceptLanguage": ",".join(profile.get("languages", ["en-US", "en"])),
    }

    # Client Hints (Sec-CH-UA headers)
    brands = [
        {"brand": "Google Chrome", "version": major},
        {"brand": "Chromium", "version": major},
        {"brand": "Not/A)Brand", "version": "99"},
    ]
    params["userAgentMetadata"] = {
        "brands": brands,
        "fullVersionList": [
            {"brand": "Google Chrome", "version": browser_version},
            {"brand": "Chromium", "version": browser_version},
            {"brand": "Not/A)Brand", "version": "99.0.0.0"},
        ],
        "platform": platform,
        "platformVersion": "10.0.0" if os_type == "windows" else "14.0.0",
        "architecture": "x86",
        "model": "",
        "mobile": False,
    }

    return params


def get_script(profile: dict = None) -> str:
    if profile is None:
        profile = {}
    return make_user_agent_script(profile.get("user_agent", DEFAULT_UA))
