"""Test Phase 4: Fingerprint profile generation and validation."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slice.fingerprint.generator import generate_profile, HARDWARE_PROFILES
from slice.fingerprint.validator import validate_profile
from slice.slice import StealthBrowser

CHROME_PATH = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")


async def test_phase_4():
    print("=" * 60)
    print("Phase 4 Test: Fingerprint Profile Generator + Validator")
    print("=" * 60)

    # Test 1: Generate profiles for each OS
    print("\n[1] Generating profiles...")
    for os_type in ["windows", "macos", "linux"]:
        p = generate_profile(os=os_type)
        print(f"    {os_type}: UA={p['user_agent'][:50]}... | GPU={p['webgl']['renderer']}")
    print("    OK")

    # Test 2: Validate all preset profiles
    print("\n[2] Validating preset profiles...")
    for name, profile in HARDWARE_PROFILES.items():
        result = validate_profile(profile)
        status = "PASS" if result.is_valid else "FAIL"
        print(f"    {name}: {status}")
        if result.errors:
            for e in result.errors:
                print(f"      ERROR: {e}")
        if result.warnings:
            for w in result.warnings:
                print(f"      WARN: {w}")
        assert result.is_valid, f"Profile {name} failed validation!"
    print("    OK — all profiles valid")

    # Test 3: Validate a deliberately broken profile
    print("\n[3] Testing validation catches inconsistencies...")
    bad_profile = generate_profile(os="windows")
    bad_profile["user_agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    result = validate_profile(bad_profile)
    assert not result.is_valid, "Should have failed validation"
    print(f"    Correctly caught: {result.errors[0]}")
    print("    OK")

    # Test 4: Launch with a real profile and verify it's applied
    print("\n[4] Launching browser with Windows Intel profile...")
    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile, chrome_path=CHROME_PATH)
    page = await sb.new_page("https://example.com")

    checks = {
        "navigator.webdriver": await page.evaluate("navigator.webdriver"),
        "navigator.platform": await page.evaluate("navigator.platform"),
        "navigator.hardwareConcurrency": await page.evaluate("navigator.hardwareConcurrency"),
        "navigator.vendor": await page.evaluate("navigator.vendor"),
        "navigator.userAgent (contains Windows)": "Windows" in str(await page.evaluate("navigator.userAgent")),
    }

    for key, val in checks.items():
        print(f"    {key} = {val}")

    assert checks["navigator.webdriver"] is None
    assert checks["navigator.platform"] == "Win32"
    assert checks["navigator.hardwareConcurrency"] == 4
    assert checks["navigator.userAgent (contains Windows)"]
    print("    OK — profile applied correctly")

    # Test 5: Launch with macOS profile in another browser
    print("\n[5] Launching with macOS profile...")
    mac_profile = generate_profile(os="macos")
    sb2 = await StealthBrowser.launch(profile=mac_profile, chrome_path=CHROME_PATH)
    page2 = await sb2.new_page("https://example.com")

    mac_platform = await page2.evaluate("navigator.platform")
    mac_cores = await page2.evaluate("navigator.hardwareConcurrency")
    mac_ua = await page2.evaluate("navigator.userAgent")
    print(f"    platform={mac_platform}, cores={mac_cores}")
    print(f"    UA={mac_ua[:60]}...")
    assert mac_platform == "MacIntel"
    assert mac_cores == 8
    assert "Macintosh" in mac_ua
    print("    OK")

    await page.close()
    await page2.close()
    await sb.close()
    await sb2.close()

    print("\n" + "=" * 60)
    print("ALL PHASE 4 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_phase_4())
