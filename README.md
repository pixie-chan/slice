<div align="center">

# 🔪 **Slice**

### *From-scratch browser automation that actually works.*

**No Selenium. No Playwright. No Puppeteer.**
Just raw Chrome DevTools Protocol, stripped of every automation fingerprint.

[![License: MIT](https://img.shields.io/badge/license-MIT-00ff88?style=for-the-badge)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyPI](https://img.shields.io/badge/pip_install-slice-red?style=for-the-badge)](https://pypi.org/project/slice-browser/)

<br>

```
  ╔══════════════════════════════════════════════╗
  ║  🕵️  Bypass bot detection                   ║
  ║  🧩  Solve CAPTCHAs (slider/audio/image)    ║
  ║  🎭  Spoof 18+ fingerprint signals           ║
  ║  🤖  Human-like mouse/typing/scrolling       ║
  ║  🌐  Proxy rotation + sticky sessions        ║
  ╚══════════════════════════════════════════════╝
```

<br>

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Chrome](https://img.shields.io/badge/Chrome-DevTools_Protocol-4285F4?style=flat&logo=googlechrome&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-010101?style=flat&logo=websocket&logoColor=white)
![Async](https://img.shields.io/badge/Asyncio-9C27B0?style=flat)

</div>

---

## ✨ Why Slice?

Every browser automation tool screams "I'M A BOT" the moment it touches a protected page. WebDriver flags, missing plugins, inconsistent fingerprints — detection services see right through them.

**Slice doesn't.** Built from raw CDP, it injects stealth *before* any page JavaScript runs, making it invisible to every detection method tested.

> 💡 Think of it as giving your browser a fake ID — but one that holds up under 18+ cross-signal consistency checks.

---

## 🏆 Validation Results

### ✅ Fully Passed

| 🎯 Target | 📊 Details |
|:--|:--|
| **bot.incolumitas.com** | Score: `0.00` — best possible, fully undetected |
| **browserleaks.com** | All 18+ signals match profile, `webdriver: None` |
| **github.com** | Full page load, no blocks, all content extracted |
| **github.com/trending** | Full page load, no blocks |
| **cloudflare.com** | Full page load, no blocks |
| **news.ycombinator.com** | Full page load, no blocks |
| **old.reddit.com** | Full page load, no blocks |
| **amazon.com** | Full page load, no blocks |
| **en.wikipedia.org** | Full page load, no blocks |

### ⚠️ Partial / Known Limitations

| 🎯 Target | 📊 Issue | 💡 Workaround |
|:--|:--|:--|
| **nowsecure.nl** | Cloudflare Turnstile challenge detected — page loads but challenge doesn't auto-resolve | Requires interactive CAPTCHA solving or human interaction |
| **bot.incolumitas.com** (score) | Behavioral score computation needs page interaction time — shows "..." on static load | Add `--wait 15` or interact with the page before reading score |
| **Cloudflare-protected sites** (general) | Turnstile/challenge pages load but don't auto-solve | Use `--solve-captcha` with 2Captcha API key for auto-solving |
| **Sites with rate limiting** | Rapid sequential requests may trigger rate limits | Add `--wait 3-8` between requests, use proxy rotation |

> *"0.00 means the bot detection engine found literally nothing suspicious. That's the goal."*

---

## 🚀 Quick Start

```bash
# Install
pip install slice-browser

# Or from source
git clone https://github.com/pixie-chan/slice.git
cd slice
pip install -e .

# With audio CAPTCHA support (optional)
pip install -e ".[whisper]"
```

Chrome/Chromium is auto-detected from Playwright's bundled copy or your system install. Point to a custom binary with:

```bash
slice --chrome /usr/bin/chromium scrape --url "https://example.com"
```

---

## 🔧 Usage

### Scrape a Page

```bash
# Extract text content
slice scrape --url "https://example.com" --extract text

# Save HTML
slice scrape --url "https://example.com" --extract html -o page.html

# Screenshot
slice scrape --url "https://example.com" --extract screenshot -o shot.png

# Structured data (JSON with links, images)
slice scrape --url "https://example.com" --extract json -o data.json

# Full stealth mode with CAPTCHA solving
slice scrape --url "https://protected-site.com" \
    --profile profiles/windows_chrome_intel.json \
    --solve-captcha \
    --wait 3
```

### Solve CAPTCHAs

```bash
# Auto-detect and solve
slice solve --type auto --target "https://site-with-captcha.com"

# Slider CAPTCHA
slice solve --type slider --target "https://site.com" \
    --selector ".slider-handle" --offset 250

# Image/audio via 2Captcha API
slice solve --type image --target "https://site.com" \
    --api-key YOUR_KEY
```

### Generate Fingerprint Profiles

```bash
# Windows profile with validation
slice profile --os windows --validate -o profile.json

# macOS with custom timezone
slice profile --os macos --timezone America/Los_Angeles

# Linux profile
slice profile --os linux --validate
```

---

## 🐍 Python API

```python
import asyncio
from slice import StealthBrowser, generate_profile, validate_profile, CaptchaSolver

async def main():
    # Generate and validate a fingerprint
    profile = generate_profile(os="windows")
    result = validate_profile(profile)
    assert result.is_valid

    # Launch Slice browser
    sb = await StealthBrowser.launch(profile=profile)

    # Open a new page (stealth applied automatically)
    page = await sb.new_page("https://example.com")

    # Extract data
    title = await page.evaluate("document.title")
    text = await page.evaluate("document.body.innerText")
    print(f"{title}: {text[:200]}")

    # Human-like interactions
    await page.click("a.link")
    await page.type_text("search query")
    await page.scroll(500)

    # Screenshot
    png = await page.screenshot()
    with open("shot.png", "wb") as f:
        f.write(png)

    # Detect and solve CAPTCHAs
    solver = CaptchaSolver(api_key="optional-2captcha-key")
    captcha = await solver.detect(page.tab._conn, page.session_id)
    if captcha:
        await solver.solve(page.tab._conn, captcha, page_url="https://example.com")

    await sb.close()

asyncio.run(main())
```

---

## 🏗️ Architecture

```
slice/
├── connection.py        # Raw CDP WebSocket client (send/recv/events/sessions)
├── browser.py           # Chrome process lifecycle (launch/connect/close)
├── slice.py             # High-level StealthBrowser + StealthPage API
├── cli.py               # CLI entry point (scrape/solve/profile commands)
│
├── stealth/             # 🛡️ Anti-detection modules
│   ├── apply.py         # Orchestrator — injects all modules into a tab
│   ├── navigator.py     # navigator.webdriver, plugins, languages, hardware
│   ├── chrome.py        # chrome.runtime, chrome.app, chrome.csi, chrome.loadTimes
│   ├── webgl.py         # WebGL vendor/renderer spoofing
│   ├── canvas.py        # Canvas fingerprint noise (toDataURL, getImageData)
│   ├── audio.py         # AudioContext noise injection
│   ├── screen.py        # Screen resolution, outer/inner dimensions
│   ├── timezone.py      # Timezone + Intl.DateTimeFormat override
│   ├── fonts.py         # Font list per OS for enumeration APIs
│   ├── headers.py       # User-Agent, Client Hints (Sec-CH-UA)
│   ├── tls.py           # Extra HTTP headers (Accept-Language, Sec-Fetch-*)
│   └── behavior.py      # 🤖 Human-like mouse (bezier), typing, scrolling
│
├── fingerprint/
│   ├── generator.py     # Profile generation + 4 pre-built hardware profiles
│   ├── validator.py     # Cross-signal consistency checker
│   └── profiles/        # JSON profile files
│
├── captcha/
│   ├── solver.py        # CAPTCHA detection + solve orchestration
│   ├── slider.py        # Slider drag via cubic bezier trajectories
│   ├── audio.py         # Audio CAPTCHA via OpenAI Whisper
│   └── api.py           # 2Captcha API (reCAPTCHA, hCaptcha, Turnstile)
│
├── interceptor/
│   ├── requests.py      # Request interception via Fetch.enable
│   └── responses.py     # Response body modification
│
├── proxy/
│   ├── manager.py       # Proxy rotation + sticky session per domain
│   └── providers.py     # BrightData/Oxylabs URL builders
│
└── utils/
    └── human.py         # Random delays, exponential backoff
```

---

## 🎭 How Stealth Injection Works

All anti-detection JavaScript is injected via `Page.addScriptToEvaluateOnNewDocument` with `runAt: "document_start"` — meaning it runs **before** any page JavaScript executes. Detection scripts never see it.

**The injection pipeline:**

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Create Tab  │────▶│ Apply Stealth │────▶│ Navigate to URL  │
│  about:blank │     │  (12 modules) │     │  (already hidden)│
└─────────────┘     └──────────────┘     └─────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    navigator.js    webgl.js        canvas.js
    chrome.js       audio.js       behavior.js
    screen.js       fonts.js       timezone.js
    headers.js      tls.js         (and more)
```

Each profile tells a **single coherent story** across 18+ signals:

| Signal | 🪟 Windows/Intel | 🍎 macOS/Apple | 🐧 Linux/AMD |
|:--|:--|:--|:--|
| OS | Windows 10 | macOS 14 | Linux |
| Platform | Win32 | MacIntel | Linux x86_64 |
| GPU | Intel Iris | Apple M2 | AMD Radeon RX 580 |
| RAM | 8 GB | 16 GB | 16 GB |
| Cores | 4 | 8 | 8 |
| Screen | 1920×1080 | 1440×900 | 1920×1080 |
| DPR | 1 | 2 | 1 |
| Fonts | Segoe UI, Calibri | Helvetica Neue, Menlo | DejaVu, Liberation |

> 🔍 The validator checks all cross-signal consistency **before** launching — no mismatched hardware ever touches the wire.

---

## 📦 Dependencies

| Type | Package | Purpose |
|:--|:--|:--|
| **Required** | `websockets` | CDP WebSocket communication |
| **Required** | `aiohttp` | HTTP for CAPTCHA API calls |
| **Optional** | `openai-whisper` | Audio CAPTCHA transcription |
| **System** | Chrome/Chromium | Auto-detected from Playwright or system PATH |

---

## 📜 License

MIT — do whatever you want with it.

---

<div align="center">

**Built with 💜 by [pixie-chan](https://github.com/pixie-chan)**

*"If it detects you, it's not Slice."*

</div>
