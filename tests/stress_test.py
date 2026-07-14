#!/usr/bin/env python3
"""Stress test for Slice — hits real bot-protected sites and reports results."""

import asyncio
import json
import time
import sys
import os

# Add the project to path
sys.path.insert(0, "/home/zen/slice")

from slice import StealthBrowser, generate_profile, validate_profile


async def test_site(sb, name, url, wait=3):
    """Test a single site — returns dict with results."""
    result = {
        "site": name,
        "url": url,
        "status": "pending",
        "title": None,
        "body_len": 0,
        "screenshot": None,
        "error": None,
        "time_s": 0,
    }
    
    start = time.time()
    try:
        page = await sb.new_page(url)
        await asyncio.sleep(wait)  # Let JS fully render
        
        title = await page.evaluate("document.title")
        body = await page.evaluate("document.body ? document.body.innerText.length : 0")
        
        result["title"] = title
        result["body_len"] = body
        result["status"] = "OK"
        result["time_s"] = round(time.time() - start, 2)
        
        # Take screenshot
        shot_path = f"/tmp/slice_test_{name.replace(' ', '_').lower()}.png"
        png = await page.screenshot()
        with open(shot_path, "wb") as f:
            f.write(png)
        result["screenshot"] = shot_path
        
        await page.close()
    except Exception as e:
        result["status"] = "FAIL"
        result["error"] = str(e)[:200]
        result["time_s"] = round(time.time() - start, 2)
    
    return result


async def main():
    print("=" * 60)
    print("  SLICE STRESS TEST — Real Bot-Protected Sites")
    print("=" * 60)
    
    # Generate a Windows fingerprint
    profile = generate_profile(os="windows")
    vr = validate_profile(profile)
    print(f"\n  Fingerprint: {'VALID' if vr.is_valid else 'INVALID'}")
    print(f"  Profile: {profile.get('platform', 'unknown')}")
    
    # Launch browser
    print("\n  Launching Slice...")
    sb = await StealthBrowser.launch(profile=profile)
    print("  Browser launched.\n")
    
    # Test targets — mix of bot-protected and normal sites
    targets = [
        ("GitHub",           "https://github.com/pixie-chan/slice"),
        ("GitHub Trending",  "https://github.com/trending"),
        ("NowSecure",        "https://nowsecure.nl"),
        ("Bot Detection",    "https://bot.incolumitas.com"),
        ("BrowserLeaks",     "https://browserleaks.com/canvas"),
        ("Cloudflare",       "https://www.cloudflare.com/"),
        ("Hacker News",      "https://news.ycombinator.com"),
        ("Reddit",           "https://old.reddit.com/r/programming"),
        ("Amazon",           "https://www.amazon.com/dp/B0D5CRCX7Y"),
        ("Wikipedia",        "https://en.wikipedia.org/wiki/Main_Page"),
    ]
    
    results = []
    for name, url in targets:
        print(f"  Testing: {name} ({url})")
        r = await test_site(sb, name, url, wait=3)
        icon = "✓" if r["status"] == "OK" else "✗"
        print(f"    {icon} {r['status']} | title={r['title'][:50] if r['title'] else 'N/A'} | body={r['body_len']} chars | {r['time_s']}s")
        if r["error"]:
            print(f"    Error: {r['error'][:100]}")
        results.append(r)
        await asyncio.sleep(1)  # Be nice between sites
    
    # Summary
    ok = sum(1 for r in results if r["status"] == "OK")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    
    print("\n" + "=" * 60)
    print(f"  RESULTS: {ok}/{len(results)} passed, {fail} failed")
    print("=" * 60)
    
    for r in results:
        icon = "✓" if r["status"] == "OK" else "✗"
        print(f"  {icon} {r['site']:20s} | {r['status']:4s} | {r['body_len']:>8} chars | {r['time_s']}s")
    
    print()
    
    # Save full results
    with open("/tmp/slice_stress_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("  Full results saved to /tmp/slice_stress_results.json")
    
    await sb.close()
    print("  Browser closed. Done.\n")


if __name__ == "__main__":
    asyncio.run(main())
