"""Stealth orchestrator — injects all stealth scripts into a tab."""

from . import navigator, chrome, webgl, canvas, audio, screen, fonts, timezone, headers


def build_stealth_script(profile: dict = None) -> str:
    """Combine all stealth JavaScript injections into a single script.

    This script is injected via Page.addScriptToEvaluateOnNewDocument at
    document_start so it runs BEFORE any page JavaScript.

    Args:
        profile: Fingerprint profile dict (from fingerprint.generator).
                 If None, uses sensible defaults.
    """
    # Each module is wrapped in its own try/catch so one failure doesn't
    # prevent other modules from running.
    def _safe(name, code):
        return f"""// === {name} ===
(function() {{
try {{
{code.strip()}
}} catch(e) {{ /* [slice] {name} error ignored */ }}
}})();
"""

    parts = [
        "// === STEALTH BROWSER INJECTION ===",
        _safe("Navigator", navigator.get_all_scripts(profile)),
        _safe("Chrome API", chrome.get_script()),
        _safe("WebGL", webgl.get_script(profile)),
        _safe("Canvas", canvas.get_script(profile)),
        _safe("Audio", audio.get_script(profile)),
        _safe("Screen", screen.get_script(profile)),
        _safe("Timezone", timezone.get_script(profile)),
        _safe("User-Agent", headers.get_script(profile)),
        _safe("Fonts", fonts.get_script(profile)),
    ]
    return "\n".join(parts)


async def apply_stealth(tab, profile: dict = None) -> str:
    """Inject all stealth scripts into a tab.

    Also sets CDP-level User-Agent and headers to match the profile.

    Args:
        tab: slice.browser.Tab instance
        profile: Fingerprint profile dict

    Returns:
        The injected script identifier for later removal.
    """
    # 1. Inject all JS stealth scripts via addScriptToEvaluateOnNewDocument
    # IMPORTANT: Do NOT use worldName — scripts must run in the MAIN world
    # so that page JS sees the spoofed navigator/screen/etc. values.
    js = build_stealth_script(profile)
    identifier = await tab.add_script(js, run_at="document_start")

    # 2. Set User-Agent and Client Hints at the CDP level
    ua_params = headers.make_user_agent_cdp_params(profile)
    await tab.send("Network.setUserAgentOverride", ua_params)

    # 3. Set extra HTTP headers (Accept-Language, Sec-Fetch-*)
    from . import tls

    extra = tls.get_extra_headers(profile)
    await tab.send("Network.setExtraHTTPHeaders", {"headers": extra})

    # 4. Enable network monitoring
    await tab.send("Network.enable")

    # 5. Set device metrics to match profile
    viewport = profile.get("viewport", {"width": 1920, "height": 1080})
    await tab.send(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": viewport["width"],
            "height": viewport["height"],
            "deviceScaleFactor": profile.get("screen", {}).get(
                "device_pixel_ratio", 1
            ),
            "mobile": False,
        },
    )

    # 6. Set timezone override at CDP level
    tz = profile.get("timezone", "America/New_York")
    await tab.send("Emulation.setTimezoneOverride", {"timezoneId": tz})

    # 7. Set locale
    locale = profile.get("locale", "en-US")
    await tab.send("Emulation.setLocaleOverride", {"locale": locale})

    return identifier
