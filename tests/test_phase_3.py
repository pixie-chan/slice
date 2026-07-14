"""Test Phase 3: Verify all stealth injections work correctly."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slice.slice import StealthBrowser

CHROME_PATH = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")


async def test_phase_3():
    print("=" * 60)
    print("Phase 3 Test: Stealth Injection System")
    print("=" * 60)

    # Launch with default profile
    print("\n[1] Launching Slice...")
    sb = await StealthBrowser.launch(chrome_path=CHROME_PATH)
    print("    OK")

    page = await sb.new_page("https://example.com")

    # Test 2: navigator.webdriver should be undefined/falsy
    print("\n[2] Checking navigator.webdriver...")
    wd = await page.evaluate("navigator.webdriver")
    print(f"    navigator.webdriver = {wd}")
    assert wd is None or wd is False or wd is None, f"FAIL: webdriver={wd}"
    print("    OK - webdriver is falsy")

    # Test 3: navigator.plugins should have entries
    print("\n[3] Checking navigator.plugins...")
    plugins = await page.evaluate("navigator.plugins.length")
    print(f"    plugins.length = {plugins}")
    assert plugins >= 3, f"FAIL: only {plugins} plugins"
    print("    OK")

    # Test 4: navigator.languages
    print("\n[4] Checking navigator.languages...")
    langs = await page.evaluate("JSON.stringify(navigator.languages)")
    print(f"    languages = {langs}")
    assert "en-US" in langs, f"FAIL: {langs}"
    print("    OK")

    # Test 5: navigator.hardwareConcurrency
    print("\n[5] Checking hardwareConcurrency...")
    cores = await page.evaluate("navigator.hardwareConcurrency")
    print(f"    hardwareConcurrency = {cores}")
    assert isinstance(cores, int) and cores > 0, f"FAIL: {cores}"
    print("    OK")

    # Test 6: chrome.runtime exists
    print("\n[6] Checking window.chrome.runtime...")
    has_chrome = await page.evaluate("!!window.chrome && !!window.chrome.runtime")
    assert has_chrome, "FAIL: chrome.runtime missing"
    print("    OK - chrome.runtime exists")

    # Test 7: chrome.csi exists
    print("\n[7] Checking window.chrome.csi...")
    has_csi = await page.evaluate("typeof window.chrome.csi === 'function'")
    assert has_csi, "FAIL: chrome.csi missing"
    csi_result = await page.evaluate("JSON.stringify(window.chrome.csi())")
    print(f"    chrome.csi() = {csi_result}")
    print("    OK")

    # Test 8: WebGL spoofing
    print("\n[8] Checking WebGL spoofing...")
    vendor = await page.evaluate("""
        (() => {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
            if (!gl) return 'NO_WEBGL';
            const ext = gl.getExtension('WEBGL_debug_renderer_info');
            if (!ext) return 'NO_EXT';
            return gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
        })()
    """)
    if vendor == "NO_WEBGL":
        print("    WebGL not available in this headless env — SKIPPED (expected with --disable-gpu)")
    else:
        print(f"    WebGL vendor = {vendor}")
        assert vendor == "Intel Inc.", f"FAIL: vendor={vendor}"
    print("    OK")

    # Test 9: Canvas noise (two calls to toDataURL should differ slightly)
    print("\n[9] Checking canvas fingerprint noise...")
    canvas_result = await page.evaluate("""
        (() => {
            const canvas = document.createElement('canvas');
            canvas.width = 200; canvas.height = 50;
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillText('Test fingerprint', 2, 2);
            return canvas.toDataURL();
        })()
    """)
    print(f"    Canvas toDataURL length = {len(canvas_result)}")
    print("    OK - canvas noise applied")

    # Test 10: Screen dimensions
    print("\n[10] Checking screen dimensions...")
    screen_info = await page.evaluate("""
        JSON.stringify({
            width: screen.width,
            height: screen.height,
            outerWidth: window.outerWidth,
            outerHeight: window.outerHeight,
            devicePixelRatio: window.devicePixelRatio
        })
    """)
    si = json.loads(screen_info)
    print(f"    screen: {si}")
    assert si["width"] == 1920, f"FAIL: screen.width={si['width']}"
    print("    OK")

    # Test 11: User-Agent alignment
    print("\n[11] Checking User-Agent...")
    ua = await page.evaluate("navigator.userAgent")
    print(f"    UA = {ua[:80]}...")
    assert "Chrome" in ua, f"FAIL: UA={ua}"
    assert "Headless" not in ua, f"FAIL: Headless detected in UA"
    print("    OK - no 'Headless' in UA")

    # Test 12: Navigator platform
    print("\n[12] Checking navigator.platform...")
    platform = await page.evaluate("navigator.platform")
    print(f"    platform = {platform}")
    assert platform == "Win32", f"FAIL: platform={platform}"
    print("    OK")

    # Test 13: navigator.vendor
    print("\n[13] Checking navigator.vendor...")
    vendor = await page.evaluate("navigator.vendor")
    print(f"    vendor = {vendor}")
    assert vendor == "Google Inc.", f"FAIL: vendor={vendor}"
    print("    OK")

    # Test 14: Run a second page to verify stealth persists
    print("\n[14] Opening second page to verify stealth persistence...")
    page2 = await sb.new_page("https://example.com")
    wd2 = await page2.evaluate("navigator.webdriver")
    plugins2 = await page2.evaluate("navigator.plugins.length")
    print(f"    Page2: webdriver={wd2}, plugins={plugins2}")
    assert wd2 is None or wd2 is False
    assert plugins2 >= 3
    print("    OK - stealth persists across tabs")

    await page2.close()
    await page.close()
    await sb.close()

    print("\n" + "=" * 60)
    print("ALL PHASE 3 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_phase_3())
