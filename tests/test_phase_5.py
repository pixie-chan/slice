"""Test Phase 5: CAPTCHA solvers (slider trajectory, detection, orchestrator)."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slice.captcha.slider import generate_slider_path
from slice.captcha.solver import CaptchaSolver
from slice.browser import Browser

CHROME_PATH = os.path.expanduser("~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome")


def test_slider_trajectory():
    """Test that slider trajectory is realistic."""
    path = generate_slider_path(100, 400, duration_ms=400)

    # Should have points
    assert len(path) > 10, f"Too few points: {len(path)}"

    # All points should be tuples of (x, y, timestamp)
    for pt in path:
        assert len(pt) == 3, f"Bad point format: {pt}"
        assert isinstance(pt[0], int), f"x not int: {pt}"
        assert isinstance(pt[1], int), f"y not int: {pt}"
        assert isinstance(pt[2], int), f"timestamp not int: {pt}"

    # X should generally increase (left to right)
    xs = [p[0] for p in path]
    assert xs[-1] >= xs[0] - 10, "Path should move right"

    # Timestamps should be non-decreasing
    timestamps = [p[2] for p in path]
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i-1], "Timestamps should increase"

    # Should have overshoot (last point should be near end_x, not past it)
    # The last two points should correct back
    assert xs[-1] <= 410, f"Overshoot too large: {xs[-1]}"

    # Y should vary (not a perfectly straight line)
    ys = [p[1] for p in path]
    y_range = max(ys) - min(ys)
    assert y_range > 0, "Y should vary (human-like jitter)"

    return len(path), xs[-1]


async def test_captcha_detection():
    """Test CAPTCHA detection on a page with no CAPTCHAs."""
    browser = await Browser.launch(chrome_path=CHROME_PATH)
    tab = await browser.new_tab("https://example.com")

    solver = CaptchaSolver()
    result = await solver.detect(tab._conn, tab.session_id)

    # example.com should have no CAPTCHAs
    assert result is None, f"False positive: detected CAPTCHA on example.com: {result}"

    await browser.close()


async def test_captcha_detection_with_mock():
    """Test detection by injecting a fake reCAPTCHA element."""
    browser = await Browser.launch(chrome_path=CHROME_PATH)
    tab = await browser.new_tab("about:blank")

    # Inject a fake reCAPTCHA div
    await tab.evaluate("""
        const div = document.createElement('div');
        div.className = 'g-recaptcha';
        div.setAttribute('data-sitekey', '6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI');
        document.body.appendChild(div);
    """)

    solver = CaptchaSolver()
    result = await solver.detect(tab._conn, tab.session_id)

    assert result is not None, "Should detect the injected reCAPTCHA"
    assert result["type"] == "recaptcha_v2", f"Wrong type: {result['type']}"
    assert result["siteKey"] == "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"

    await browser.close()
    return result


async def test_phase_5():
    print("=" * 60)
    print("Phase 5 Test: CAPTCHA Solvers")
    print("=" * 60)

    # Test 1: Slider trajectory
    print("\n[1] Testing slider trajectory generation...")
    num_points, final_x = test_slider_trajectory()
    print(f"    {num_points} points, final x={final_x}")
    print("    OK")

    # Test 2: Multiple trajectories are different (randomness)
    print("\n[2] Testing trajectory randomness...")
    path1 = generate_slider_path(100, 400)
    path2 = generate_slider_path(100, 400)
    # At least some points should differ
    diffs = sum(1 for a, b in zip(path1, path2) if a[0] != b[0] or a[1] != b[1])
    assert diffs > 5, f"Trajectories too similar: only {diffs} differences"
    print(f"    {diffs} points differ between trajectories")
    print("    OK")

    # Test 3: Detection on clean page
    print("\n[3] Testing CAPTCHA detection (clean page)...")
    await test_captcha_detection()
    print("    OK — no false positive on example.com")

    # Test 4: Detection with mock CAPTCHA
    print("\n[4] Testing CAPTCHA detection (mock reCAPTCHA)...")
    result = await test_captcha_detection_with_mock()
    print(f"    Detected: {result['type']} with siteKey={result['siteKey'][:20]}...")
    print("    OK")

    print("\n" + "=" * 60)
    print("ALL PHASE 5 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_phase_5())
