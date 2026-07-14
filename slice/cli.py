"""Stealth Browser CLI — command-line interface for scraping, solving CAPTCHAs, and profile management.

Usage:
    slice scrape --url URL [--extract text|html|screenshot] [--output FILE] [--profile FILE]
    slice solve  --type image|slider|audio --target URL [--selector SEL]
    slice profile --os windows|macos|linux [--output FILE]
"""

import argparse
import asyncio
import json
import logging
import os
import sys

# Allow running as `python -m slice.cli` or `python cli.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slice.browser import Browser
from slice.stealth_browser import StealthBrowser
from slice.fingerprint.generator import generate_profile, save_profile, load_profile
from slice.fingerprint.validator import validate_profile
from slice.captcha.solver import CaptchaSolver
from slice.captcha.slider import solve_slider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_chrome() -> str | None:
    """Find Chrome/Chromium binary (mirrors browser.py logic)."""
    import glob as _glob
    import shutil

    # Playwright bundled Chromium
    for p in sorted(_glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"
    )), reverse=True):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p

    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(candidate)
        if path:
            return path

    for path in (
        "/usr/bin/google-chrome", "/usr/bin/chromium",
        "/opt/google/chrome/chrome", "/snap/bin/chromium",
    ):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return None


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Silence noisy libraries
    logging.getLogger("websockets").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_scrape(args: argparse.Namespace) -> None:
    """Scrape a URL: extract text, full HTML, or take a screenshot."""
    chrome = args.chrome or _find_chrome()
    if not chrome:
        print("ERROR: Chrome/Chromium not found. Use --chrome or install Chromium.", file=sys.stderr)
        sys.exit(1)

    profile = None
    if args.profile:
        profile = load_profile(args.profile)
        print(f"Loaded profile: {profile.get('os', '?')} / {profile.get('browser', '?')}")

    sb = await StealthBrowser.launch(profile=profile, chrome_path=chrome, headless=not args.visible)

    try:
        page = await sb.new_page(args.url)

        # Optional wait
        if args.wait:
            await asyncio.sleep(args.wait)

        extract = args.extract

        if extract == "text":
            content = await page.evaluate("document.body.innerText")
            if args.output:
                with open(args.output, "w") as f:
                    f.write(content)
                print(f"Text saved to {args.output} ({len(content)} chars)")
            else:
                print(content)

        elif extract == "html":
            content = await page.evaluate("document.documentElement.outerHTML")
            if args.output:
                with open(args.output, "w") as f:
                    f.write(content)
                print(f"HTML saved to {args.output} ({len(content)} chars)")
            else:
                print(content)

        elif extract == "screenshot":
            png = await page.screenshot()
            out = args.output or "screenshot.png"
            with open(out, "wb") as f:
                f.write(png)
            print(f"Screenshot saved to {out} ({len(png)} bytes)")

        elif extract == "json":
            data = await page.evaluate("""
            JSON.stringify({
                url: window.location.href,
                title: document.title,
                text: document.body.innerText,
                links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim(),
                    href: a.href
                })).filter(l => l.text && l.href.startsWith('http')),
                images: Array.from(document.querySelectorAll('img[src]')).map(i => ({
                    alt: i.alt,
                    src: i.src
                }))
            })
            """)
            result = json.loads(data)
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"JSON saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))

        # Detect CAPTCHAs
        solver = CaptchaSolver()
        captcha = await solver.detect(page.tab._conn, page.session_id)
        if captcha:
            print(f"\nCAPTCHA detected: {captcha['type']}")
            if args.solve_captcha:
                print("Attempting to solve...")
                result = await solver.solve(
                    page.tab._conn, captcha, page_url=args.url, session_id=page.session_id
                )
                if result:
                    print(f"CAPTCHA solved: {result[:50]}...")
                else:
                    print("Could not solve CAPTCHA automatically.")

    finally:
        await sb.close()


async def cmd_solve(args: argparse.Namespace) -> None:
    """Solve a CAPTCHA on a target page."""
    chrome = args.chrome or _find_chrome()
    if not chrome:
        print("ERROR: Chrome/Chromium not found.", file=sys.stderr)
        sys.exit(1)

    sb = await StealthBrowser.launch(chrome_path=chrome, headless=not args.visible)

    try:
        page = await sb.new_page(args.target)
        await asyncio.sleep(3)

        solver = CaptchaSolver(api_key=args.api_key)

        if args.type == "auto":
            # Auto-detect and solve
            captcha = await solver.detect(page.tab._conn, page.session_id)
            if not captcha:
                print("No CAPTCHA detected on page.")
                return
            print(f"Detected: {captcha['type']}")
            result = await solver.solve(
                page.tab._conn, captcha, page_url=args.target, session_id=page.session_id
            )
        elif args.type == "slider":
            if not args.selector:
                print("ERROR: --selector required for slider CAPTCHA", file=sys.stderr)
                sys.exit(1)
            offset = args.offset or 200
            await solve_slider(page.tab._conn, args.selector, offset, page.session_id)
            result = "solved"
        else:
            # image / audio — use solver
            captcha = {"type": args.type, "selector": args.selector or ""}
            result = await solver.solve(
                page.tab._conn, captcha, page_url=args.target, session_id=page.session_id
            )

        if result:
            print(f"Result: {result}")
        else:
            print("Could not solve CAPTCHA.")

    finally:
        await sb.close()


async def cmd_profile(args: argparse.Namespace) -> None:
    """Generate and optionally validate a fingerprint profile."""
    profile = generate_profile(
        os=args.os,
        timezone=args.timezone,
        locale=args.locale,
    )

    # Validate
    result = validate_profile(profile)
    if args.validate:
        print(result)
        if not result.is_valid:
            sys.exit(1)

    # Save or print
    out = args.output
    if out:
        save_profile(profile, out)
        print(f"Profile saved to {out}")
    else:
        print(json.dumps(profile, indent=2))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stealth-browser",
        description="Stealth browser automation — raw CDP, no Selenium/Playwright/Puppeteer",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--chrome", type=str, default=None, help="Path to Chrome/Chromium binary")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ---- scrape ----
    sp = sub.add_parser("scrape", help="Scrape a URL with stealth browser")
    sp.add_argument("--url", required=True, help="URL to scrape")
    sp.add_argument(
        "--extract", choices=["text", "html", "screenshot", "json"],
        default="text", help="What to extract (default: text)",
    )
    sp.add_argument("--output", "-o", type=str, help="Output file path")
    sp.add_argument("--profile", type=str, help="Fingerprint profile JSON file")
    sp.add_argument("--wait", type=float, default=0, help="Extra seconds to wait after load")
    sp.add_argument("--solve-captcha", action="store_true", help="Auto-solve CAPTCHAs if detected")
    sp.add_argument("--visible", action="store_true", help="Run in visible (non-headless) mode")

    # ---- solve ----
    sp = sub.add_parser("solve", help="Solve a CAPTCHA")
    sp.add_argument("--type", choices=["auto", "image", "slider", "audio"], default="auto",
                     help="CAPTCHA type (default: auto-detect)")
    sp.add_argument("--target", required=True, help="URL containing the CAPTCHA")
    sp.add_argument("--selector", type=str, help="CSS selector for the CAPTCHA element")
    sp.add_argument("--offset", type=int, help="Slider drag offset in pixels")
    sp.add_argument("--api-key", type=str, help="2Captcha API key (for remote solving)")
    sp.add_argument("--visible", action="store_true", help="Run in visible mode")

    # ---- profile ----
    sp = sub.add_parser("profile", help="Generate a fingerprint profile")
    sp.add_argument("--os", choices=["windows", "macos", "linux"], default="windows",
                     help="Target OS (default: windows)")
    sp.add_argument("--timezone", type=str, help="Timezone (e.g. America/Chicago)")
    sp.add_argument("--locale", type=str, help="Locale (e.g. en-US)")
    sp.add_argument("--output", "-o", type=str, help="Save profile to JSON file")
    sp.add_argument("--validate", action="store_true", help="Validate profile consistency")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    _setup_logging(args.verbose)

    cmd_map = {
        "scrape": cmd_scrape,
        "solve": cmd_solve,
        "profile": cmd_profile,
    }

    try:
        asyncio.run(cmd_map[args.command](args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
