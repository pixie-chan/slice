"""End-to-end test: nowsecure.nl (Cloudflare Turnstile) + browserleaks.com + pixelscan.net"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slice.fingerprint.generator import generate_profile
from slice.slice import StealthBrowser

CHROME_PATH = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")


async def test_nowsecure():
    """Test against nowsecure.nl which uses Cloudflare Turnstile."""
    print("\n[1] Testing against nowsecure.nl (Cloudflare Turnstile)...")
    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile, chrome_path=CHROME_PATH)
    page = await sb.new_page("https://nowsecure.nl")

    # Wait for Cloudflare challenge to process
    print("    Waiting for Cloudflare challenge...")
    await asyncio.sleep(10)

    url = await page.get_url()
    print(f"    Current URL: {url}")

    body = await page.evaluate("document.body.innerText")
    print(f"    Page content preview: {body[:200]}...")

    screenshot = await page.screenshot()
    with open("nowsecure_screenshot.png", "wb") as f:
        f.write(screenshot)
    print(f"    Screenshot saved ({len(screenshot)} bytes)")

    await sb.close()
    return url


async def test_browserleaks():
    """Test against browserleaks.com for fingerprint analysis."""
    print("\n[2] Testing against browserleaks.com...")
    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile, chrome_path=CHROME_PATH)
    page = await sb.new_page("https://browserleaks.com")
    await asyncio.sleep(3)

    # Gather all fingerprint data
    fp = await page.evaluate("""
    JSON.stringify({
        browser: navigator.userAgent,
        platform: navigator.platform,
        vendor: navigator.vendor,
        languages: navigator.languages,
        plugins: navigator.plugins.length,
        hardwareConcurrency: navigator.hardwareConcurrency,
        deviceMemory: navigator.deviceMemory,
        webdriver: navigator.webdriver,
        screenW: screen.width,
        screenH: screen.height,
        colorDepth: screen.colorDepth,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        cookieEnabled: navigator.cookieEnabled,
        doNotTrack: navigator.doNotTrack,
    })
    """)
    data = json.loads(fp)

    print("    Fingerprint data:")
    for k, v in data.items():
        marker = "  " if v is not None else " *"
        print(f"    {marker} {k}: {v}")

    if data.get("webdriver") is None:
        print("\n    PASS: webdriver hidden")
    else:
        print(f"\n    FAIL: webdriver={data['webdriver']}")

    screenshot = await page.screenshot()
    with open("e2e_browserleaks.png", "wb") as f:
        f.write(screenshot)

    await sb.close()
    return data


async def test_pixelscan():
    """Test against pixelscan.net."""
    print("\n[3] Testing against pixelscan.net...")
    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile, chrome_path=CHROME_PATH)
    page = await sb.new_page("https://pixelscan.net")
    await asyncio.sleep(5)

    body = await page.evaluate("document.body.innerText")

    screenshot = await page.screenshot()
    with open("pixelscan_screenshot.png", "wb") as f:
        f.write(screenshot)
    print(f"    Screenshot saved ({len(screenshot)} bytes)")

    # Check for common detection indicators
    if "bot detected" in body.lower() or "automation detected" in body.lower():
        print("    WARNING: Detection indicated")
    elif "consistent" in body.lower():
        print("    PASS: Fingerprint appears consistent")
    else:
        print(f"    Page preview: {body[:300]}...")

    await sb.close()


async def main():
    print("=" * 60)
    print("End-to-End Stealth Validation")
    print("=" * 60)

    await test_nowsecure()
    fp = await test_browserleaks()
    await test_pixelscan()

    print("\n" + "=" * 60)
    print("END-TO-END VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
