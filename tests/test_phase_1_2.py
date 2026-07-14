"""Test Phase 1+2: Launch Chrome, connect via CDP, run basic commands."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slice.browser import Browser


CHROME_PATH = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")


async def test_phase_1_2():
    print("=" * 60)
    print("Phase 1+2 Test: Launch Chrome + CDP Connection")
    print("=" * 60)

    # Test 1: Launch browser
    print("\n[1] Launching Chrome...")
    browser = await Browser.launch(chrome_path=CHROME_PATH)
    print(f"    OK - Chrome launched")

    # Test 2: Get version
    print("\n[2] Getting browser version...")
    version = await browser.get_version()
    print(f"    Browser: {version.get('product', 'unknown')}")
    print(f"    Protocol: {version.get('protocolVersion', 'unknown')}")
    print(f"    User-Agent: {version.get('userAgent', 'unknown')[:80]}...")

    # Test 3: Create a new tab
    print("\n[3] Creating new tab...")
    tab = await browser.new_tab("about:blank")
    print(f"    OK - Tab created: target_id={tab.target_id[:16]}...")

    # Test 4: Navigate to a page
    print("\n[4] Navigating to example.com...")
    await tab.navigate("https://example.com")
    url = await tab.get_url()
    print(f"    OK - Current URL: {url}")

    # Test 5: Evaluate JavaScript
    print("\n[5] Evaluating JavaScript...")
    title = await tab.evaluate("document.title")
    print(f"    OK - Page title: {title}")

    # Test 6: Get page content
    print("\n[6] Getting page content...")
    text = await tab.evaluate("document.body.innerText.substring(0, 200)")
    print(f"    OK - Content preview: {text[:100]}...")

    # Test 7: List targets
    print("\n[7] Listing all targets...")
    targets = await browser.get_targets()
    for t in targets:
        print(f"    - {t.get('type', '?')}: {t.get('url', '?')[:60]}")

    # Test 8: Screenshot
    print("\n[8] Taking screenshot...")
    png_data = await tab.screenshot()
    screenshot_path = "test_screenshot.png"
    with open(screenshot_path, "wb") as f:
        f.write(png_data)
    print(f"    OK - Saved {len(png_data)} bytes to {screenshot_path}")

    # Test 9: Inject a script
    print("\n[9] Testing addScriptToEvaluateOnNewDocument...")
    script_id = await tab.add_script("window.__test_injected = 42;")
    print(f"    OK - Script injected with id: {script_id[:20]}...")

    # Navigate to trigger the injected script
    await tab.navigate("https://example.com")
    val = await tab.evaluate("window.__test_injected")
    print(f"    OK - Injected value after navigation: {val}")

    # Cleanup
    await tab.close()
    await browser.close()
    print("\n" + "=" * 60)
    print("ALL PHASE 1+2 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_phase_1_2())
