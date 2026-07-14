# SKILL.md — Slice Automation

## When to use

Use the Slice skill when the user needs to:

- Scrape websites that have bot detection (Cloudflare, Akamai, PerimeterX, DataDome)
- Automate browser interactions without triggering anti-bot systems
- Extract data from JavaScript-heavy or SPA websites
- Solve CAPTCHAs (slider, image, audio, reCAPTCHA, hCaptcha, Cloudflare Turnstile)
- Test a website's bot detection defenses
- Generate realistic browser fingerprint profiles
- Take screenshots of protected pages

## Key capabilities

- **Raw CDP over WebSocket** — no Selenium, Playwright, or Puppeteer dependency
- **Full stealth injection** — navigator.webdriver removal, plugin spoofing, chrome.runtime/csi/loadTimes, WebGL spoofing, canvas noise, audio fingerprint noise, screen dimension spoofing, timezone/locale alignment
- **Fingerprint profiles** — 4 pre-built profiles (Windows/Intel, macOS/Apple, Linux/AMD, Windows/NVIDIA) with consistency validation
- **CAPTCHA solving** — slider (bezier trajectory), audio (Whisper transcription), API fallback (2Captcha)
- **Human-like behavior** — bezier mouse movement, variable typing delays, natural scroll
- **Request interception** — header modification via CDP Fetch domain
- **Proxy management** — rotation, sticky sessions, BrightData/Oxylabs helpers

## Installation

```bash
cd slice
pip install --break-system-packages -e .
```

## CLI commands

### Scrape a page

```bash
slice scrape --url "https://example.com" --extract text
slice scrape --url "https://example.com" --extract html --output page.html
slice scrape --url "https://example.com" --extract screenshot --output shot.png
slice scrape --url "https://example.com" --extract json --output data.json
slice scrape --url "https://example.com" --profile profile.json --solve-captcha
```

Options:
- `--extract text|html|screenshot|json` — what to extract (default: text)
- `--output FILE` — save output to file
- `--profile FILE` — use a fingerprint profile JSON
- `--wait SECONDS` — extra wait after page load
- `--solve-captcha` — auto-detect and solve CAPTCHAs
- `--visible` — run non-headless

### Solve a CAPTCHA

```bash
slice solve --type auto --target "https://example.com/captcha"
slice solve --type slider --target "https://example.com" --selector ".slider-handle" --offset 250
slice solve --type image --target "https://example.com" --api-key YOUR_2CAPTCHA_KEY
```

Options:
- `--type auto|image|slider|audio` — CAPTCHA type (default: auto-detect)
- `--selector CSS` — CSS selector for the CAPTCHA element
- `--offset PIXELS` — slider drag distance
- `--api-key KEY` — 2Captcha API key for remote solving

### Generate a fingerprint profile

```bash
slice profile --os windows --validate --output profile.json
slice profile --os macos --timezone America/Los_Angeles
slice profile --os linux --validate
```

Options:
- `--os windows|macos|linux` — target OS
- `--timezone TZ` — override timezone
- `--locale LOCALE` — override locale
- `--validate` — check profile consistency before saving

## Python API

```python
import asyncio
from slice import StealthBrowser, generate_profile, CaptchaSolver

async def main():
    profile = generate_profile(os="windows")
    sb = await StealthBrowser.launch(profile=profile)
    page = await sb.new_page("https://example.com")

    text = await page.evaluate("document.body.innerText")
    await page.screenshot()  # bytes

    await sb.close()

asyncio.run(main())
```

## File structure

```
slice/
├── __init__.py              # Public API exports
├── cli.py                   # CLI entry point
├── browser.py               # Chrome launch + CDP lifecycle
├── connection.py            # Raw WebSocket CDP client
├── slice.py       # High-level StealthBrowser/StealthPage
├── stealth/
│   ├── apply.py             # Stealth orchestrator (injects all modules)
│   ├── navigator.py         # webdriver, plugins, languages, hardware
│   ├── chrome.py            # chrome.runtime, chrome.csi, chrome.loadTimes
│   ├── webgl.py             # WebGL vendor/renderer spoofing
│   ├── canvas.py            # Canvas fingerprint noise
│   ├── audio.py             # AudioContext noise
│   ├── screen.py            # Screen/window dimensions
│   ├── timezone.py          # Timezone/locale override
│   ├── fonts.py             # Font list generation
│   ├── headers.py           # User-Agent + Client Hints
│   ├── tls.py               # Extra HTTP headers
│   └── behavior.py          # Human mouse/type/scroll
├── fingerprint/
│   ├── generator.py         # Profile generation + presets
│   ├── validator.py         # Consistency checks
│   └── profiles/            # Pre-built JSON profiles
├── captcha/
│   ├── solver.py            # Detection + orchestration
│   ├── slider.py            # Bezier trajectory solver
│   ├── audio.py             # Whisper-based solver
│   └── api.py               # 2Captcha API wrapper
├── interceptor/
│   ├── requests.py          # Request interception/modification
│   └── responses.py         # Response modification
├── proxy/
│   ├── manager.py           # Rotation + sticky sessions
│   └── providers.py         # BrightData/Oxylabs helpers
└── utils/
    └── human.py             # Random delays, backoff
```

## Important constraints

- Chrome/Chromium must be installed (auto-detected, or use `--chrome PATH`)
- All stealth JS runs via `Page.addScriptToEvaluateOnNewDocument` at `document_start`
- Fingerprint consistency is critical — all 18+ signals must tell the same story
- For production scraping, use residential proxies (IP reputation > fingerprint)
- Each domain should get its own proxy + cookies (never reuse sessions)
- Respect robots.txt and rate limit (2-8 second delays between requests)
- Audio CAPTCHA solving requires the optional `openai-whisper` dependency

## Validation results

Tested against real bot detection services:
- **bot.incolumitas.com** — Total Bot Score: 0.00 (best possible)
- **nowsecure.nl** — "This browser has passed our bot detection test"
- **browserleaks.com** — All signals match profile (Windows 10, Chrome 126, Intel Iris)
