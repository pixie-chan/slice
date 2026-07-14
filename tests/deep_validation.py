#!/usr/bin/env python3
"""Deep validation — bot detection tests with interaction and polling."""

import asyncio, json, sys, re
sys.path.insert(0, "/home/zen/slice")
from slice import StealthBrowser, generate_profile
from slice.stealth.behavior import human_scroll, human_move_to, human_type, human_click


async def test_nowsecure(sb):
    """Test nowsecure.nl — Cloudflare Turnstile bypass test."""
    print("=" * 60)
    print("  NOWSECURE.NL — Cloudflare Turnstile Test")
    print("=" * 60)

    page = await sb.new_page("https://nowsecure.nl")
    await asyncio.sleep(3)

    body = ""
    for i in range(12):
        body = await page.evaluate("document.body ? document.body.innerText || '' : ''")
        title = await page.evaluate("document.title || ''")

        if "This browser has passed" in body or "YOU ARE A HUMAN" in body.upper():
            print(f"  \u2713 PASSED NOWSECURE TEST (after {i * 1}s)")
            for line in body.split("\n"):
                l = line.strip()
                if l and ("passed" in l.lower() or "human" in l.lower() or "bot" in l.lower()):
                    print(f"  > {l[:120]}")
            break
        elif "challenge" in body.lower() or "turnstile" in body.lower():
            await human_scroll(page.tab._conn, 300, session_id=page.session_id)
            await human_move_to(page.tab._conn, 600, 400, session_id=page.session_id)
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(1)
    else:
        print(f"  \u2717 NowSecure did not show pass/fail after 15s")
        print(f"  Body preview: {body[:300]}")
        if "nodriver" in body.lower() or "by nodriver" in body.lower():
            print(f"  \u26a0 DETECTED AS AUTOMATED (nodriver reference found)")

    png = await page.screenshot()
    with open("/tmp/nowsecure_result.png", "wb") as f:
        f.write(png)
    await page.close()
    return "passed" in body.lower()


async def test_bot_score(sb):
    """Test bot.incolumitas.com with interaction and score polling."""
    print("\n" + "=" * 60)
    print("  BOT.INCOLUMITAS.COM — Behavioral Score")
    print("=" * 60)

    page = await sb.new_page("https://bot.incolumitas.com")
    await asyncio.sleep(2)

    # Intercept dialog (alert/confirm) to auto-accept
    page.tab._conn.on("Page.javascriptDialogOpening", lambda p: asyncio.ensure_future(
        page.tab.send("Page.handleJavaScriptDialog", {"accept": True})
    ))

    # Simulate human-like interaction: scroll and move
    await human_scroll(page.tab._conn, 300, session_id=page.session_id)
    await asyncio.sleep(0.5)
    await human_scroll(page.tab._conn, 600, session_id=page.session_id)
    await asyncio.sleep(0.5)
    await human_move_to(page.tab._conn, 800, 500, session_id=page.session_id)
    await asyncio.sleep(0.5)

    # Try to fill out the Bot Challenge form if present
    try:
        has_form = await page.evaluate("""
            (() => {
                const input = document.querySelector('input[type="text"], input[name], input[id]');
                const btn = document.querySelector('button, input[type="submit"], input[type="button"]');
                return !!(input && btn);
            })()
        """)
        if has_form:
            # Click the input to focus it first
            input_rect = await page.evaluate("""
                (() => {
                    const el = document.querySelector('input[type="text"], input[name], input[id]');
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
                })()
            """)
            if input_rect:
                import json as _json
                rect = _json.loads(input_rect)
                await human_click(page.tab._conn, rect['x'], rect['y'], page.session_id)
                await asyncio.sleep(0.3)
            
            # Type using CDP keyboard events for real behavioral signals
            await human_type(page.tab._conn, 'human user test', page.session_id)
            await asyncio.sleep(0.5)
            
            # Click the submit button
            btn_rect = await page.evaluate("""
                (() => {
                    const el = document.querySelector('button, input[type="submit"], input[type="button"]');
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
                })()
            """)
            if btn_rect:
                rect = _json.loads(btn_rect)
                await human_click(page.tab._conn, rect['x'], rect['y'], page.session_id)
                await asyncio.sleep(1)
            print(f"  Completed bot challenge form + dialog")
    except Exception as e:
        print(f"  Form interaction note: {e}")

    # More scrolling after form submission
    await human_scroll(page.tab._conn, -400, session_id=page.session_id)
    await asyncio.sleep(1)
    await human_scroll(page.tab._conn, 200, session_id=page.session_id)
    await asyncio.sleep(0.5)

    # Poll for score
    score = None
    for i in range(20):
        body = await page.evaluate("document.body ? document.body.innerText || '' : ''")
        for line in body.split("\n"):
            l = line.strip()
            if l and ("Your Behavioral Score:" in l or "behavioralClassificationScore" in l or "behavioral" in l.lower()):
                print(f"  > {l[:120]}")
                m = re.search(r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)', l)
                if m:
                    score = float(m.group(1))
                elif not score:
                    m = re.search(r'(\d+\.\d+)', l)
                    if m:
                        score = float(m.group(1))
            elif l and "score" in l.lower() and any(c.isdigit() for c in l):
                print(f"  > {l[:120]}")
                m = re.search(r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)', l)
                if m:
                    score = float(m.group(1))

        if score is not None:
            break

        if "..." in body or "computing" in body.lower() or "waiting" in body.lower():
            await human_scroll(page.tab._conn, 100, session_id=page.session_id)
            await asyncio.sleep(2)
        else:
            await asyncio.sleep(1)

    if score is not None:
        verdict = "\u2713 GOOD" if score > 0.5 else "\u2717 POOR"
        print(f"  Final score: {score} {verdict}")
    else:
        try:
            score_el = await page.evaluate("""
                (() => {
                    const els = document.querySelectorAll('*');
                    for (const el of els) {
                        if (el.innerText && /score/i.test(el.innerText) && /\\d/.test(el.innerText)) {
                            return el.innerText.substring(0, 200);
                        }
                    }
                    return null;
                })()
            """)
            if score_el:
                print(f"  DOM score element: {score_el[:200]}")
        except Exception:
            pass
        print(f"  \u2717 Could not extract bot score after 20s")

    png = await page.screenshot()
    with open("/tmp/bot_score.png", "wb") as f:
        f.write(png)
    await page.close()
    return score


async def test_browserleaks(sb):
    """Test browserleaks.com for fingerprint consistency."""
    print("\n" + "=" * 60)
    print("  BROWSERLEAKS — FINGERPRINT CHECK")
    print("=" * 60)

    page = await sb.new_page("https://browserleaks.com/canvas")
    await asyncio.sleep(4)

    checks = {
        "navigator.webdriver": "navigator.webdriver",
        "plugins.length": "navigator.plugins.length",
        "languages": "JSON.stringify(navigator.languages)",
        "platform": "navigator.platform",
        "userAgent": "navigator.userAgent",
        "hardwareConcurrency": "navigator.hardwareConcurrency",
        "deviceMemory": "navigator.deviceMemory",
        "screen.width": "screen.width",
        "screen.height": "screen.height",
        "colorDepth": "screen.colorDepth",
        "timezone": "Intl.DateTimeFormat().resolvedOptions().timeZone",
        "Notification.permission": "Notification.permission",
    }

    for label, js in checks.items():
        try:
            val = await page.evaluate(js)
            print(f"  {label:25s} = {str(val)[:80]}")
        except Exception as e:
            print(f"  {label:25s} = ERROR: {e}")

    webdriver_val = await page.evaluate("navigator.webdriver")
    wd_ok = webdriver_val is None or webdriver_val == False
    print(f"\n  webdriver hidden: {'\u2713 YES' if wd_ok else '\u2717 NO — DETECTED!'}")

    try:
        cr = await page.evaluate("typeof window.chrome !== 'undefined' && window.chrome && 'runtime' in window.chrome")
        print(f"  chrome.runtime exists: {cr}")
    except Exception:
        print(f"  chrome.runtime exists: false")

    png = await page.screenshot()
    with open("/tmp/browserleaks_result.png", "wb") as f:
        f.write(png)
    await page.close()


async def test_rapid_fire(sb):
    """Rapid-fire 5 pages back-to-back."""
    print("\n" + "=" * 60)
    print("  RAPID-FIRE — 5 pages in sequence")
    print("=" * 60)

    rapid_targets = [
        ("GitHub", "https://github.com"),
        ("HN", "https://news.ycombinator.com"),
        ("Reddit", "https://old.reddit.com"),
        ("Amazon", "https://www.amazon.com"),
        ("Wikipedia", "https://en.wikipedia.org"),
    ]
    for name, url in rapid_targets:
        t0 = asyncio.get_event_loop().time()
        p = await sb.new_page(url)
        await asyncio.sleep(2)
        title = await p.evaluate("document.title")
        dt = round(asyncio.get_event_loop().time() - t0, 2)
        print(f"  \u2713 {name:12s} | {dt}s | {title[:50]}")
        await p.close()


async def main():
    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile)
    print(f"  Browser launched with profile: {profile.get('platform', 'unknown')}")

    try:
        ns_pass = await test_nowsecure(sb)
        bot_score = await test_bot_score(sb)
        await test_browserleaks(sb)
        await test_rapid_fire(sb)

        print("\n" + "=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"  NowSecure: {'PASS' if ns_pass else 'FAIL/UNCLEAR'}")
        print(f"  Bot Score:  {bot_score if bot_score is not None else 'not computed'}")
    finally:
        await sb.close()

    print("\n  All done. Screenshots in /tmp/")


if __name__ == "__main__":
    asyncio.run(main())
