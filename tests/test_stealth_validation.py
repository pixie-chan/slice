"""Phase 3 Validation: Test stealth against bot detection sites.

This navigates to bot.incolumitas.com and browserleaks.com to check
if our stealth measures pass real-world detection.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slice.fingerprint.generator import generate_profile
from slice.slice import StealthBrowser

CHROME_PATH = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")


async def test_bot_detection():
    print("=" * 60)
    print("Stealth Validation: Bot Detection Sites")
    print("=" * 60)

    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile, chrome_path=CHROME_PATH)

    # Test 1: bot.incolumitas.com
    print("\n[1] Testing against bot.incolumitas.com...")
    page = await sb.new_page("https://bot.incolumitas.com")
    # Wait for the detection script to run (it takes a few seconds)
    await asyncio.sleep(5)

    # Take a screenshot for visual inspection
    screenshot = await page.screenshot()
    with open("bot_test_screenshot.png", "wb") as f:
        f.write(screenshot)
    print(f"    Screenshot saved ({len(screenshot)} bytes)")

    # Try to get the detection result text
    try:
        body_text = await page.evaluate("document.body.innerText")
        # bot.incolumitas.com shows a score/result
        if "automation detected" in body_text.lower() or "bot detected" in body_text.lower():
            print("    WARNING: Bot detection triggered")
        elif "no automation" in body_text.lower() or "not detected" in body_text.lower():
            print("    PASS: No automation detected")
        else:
            print(f"    Result preview: {body_text[:300]}...")
    except Exception as e:
        print(f"    Could not read result: {e}")

    # Test 2: browserleaks.com
    print("\n[2] Testing against browserleaks.com...")
    page2 = await sb.new_page("https://browserleaks.com")
    await asyncio.sleep(3)

    # Check key fingerprint values reported by browserleaks
    checks = {}
    try:
        checks["userAgent"] = await page2.evaluate("navigator.userAgent")
        checks["platform"] = await page2.evaluate("navigator.platform")
        checks["webdriver"] = await page2.evaluate("navigator.webdriver")
        checks["plugins"] = await page2.evaluate("navigator.plugins.length")
        checks["languages"] = await page2.evaluate("navigator.languages.join(', ')")

        for k, v in checks.items():
            print(f"    {k}: {v}")

        if "Headless" in str(checks.get("userAgent", "")):
            print("    FAIL: HeadlessChrome in UA")
        else:
            print("    UA looks clean")

        if checks.get("webdriver") is None or checks.get("webdriver") is False:
            print("    webdriver: hidden")
        else:
            print(f"    WARNING: webdriver={checks['webdriver']}")
    except Exception as e:
        print(f"    Error checking: {e}")

    screenshot2 = await page2.screenshot()
    with open("browserleaks_screenshot.png", "wb") as f:
        f.write(screenshot2)
    print(f"    Screenshot saved ({len(screenshot2)} bytes)")

    # Test 3: Check our own stealth signals comprehensively
    print("\n[3] Comprehensive stealth signal check...")
    page3 = await sb.new_page("https://example.com")
    signals = await page3.evaluate("""
    JSON.stringify({
        webdriver: navigator.webdriver,
        platform: navigator.platform,
        userAgent: navigator.userAgent,
        plugins: navigator.plugins.length,
        languages: navigator.languages.join(', '),
        hardwareConcurrency: navigator.hardwareConcurrency,
        deviceMemory: navigator.deviceMemory,
        vendor: navigator.vendor,
        hasChrome: !!window.chrome,
        hasChromeRuntime: !!(window.chrome && window.chrome.runtime),
        hasChromeCsi: !!(window.chrome && window.chrome.csi),
        screenWidth: screen.width,
        screenHeight: screen.height,
        outerWidth: window.outerWidth,
        outerHeight: window.outerHeight,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        touchSupport: navigator.maxTouchPoints,
        cookieEnabled: navigator.cookieEnabled,
    })
    """)
    sig = json.loads(signals)
    for k, v in sig.items():
        print(f"    {k}: {v}")

    # Verify critical signals
    issues = []
    if sig.get("webdriver") is not None and sig.get("webdriver") is not False:
        issues.append(f"webdriver={sig.get('webdriver')}")
    if "Headless" in sig.get("userAgent", ""):
        issues.append("Headless in UA")
    if "Win32" not in sig.get("platform", ""):
        issues.append(f"platform={sig.get('platform')}")
    if sig.get("plugins", 0) < 3:
        issues.append(f"only {sig.get('plugins', 0)} plugins")
    if not sig.get("hasChromeRuntime"):
        issues.append("chrome.runtime missing")
    if sig.get("screenWidth") != 1920:
        issues.append(f"screen.width={sig.get('screenWidth')}")

    if issues:
        print(f"\n    ISSUES FOUND: {', '.join(issues)}")
    else:
        print("\n    ALL CRITICAL SIGNALS PASS")

    await page.close()
    await page2.close()
    await page3.close()
    await sb.close()

    print("\n" + "=" * 60)
    print("STEALTH VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_bot_detection())
