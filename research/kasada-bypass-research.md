# Kasada Bot Protection — Bypass Research

**Date:** July 14, 2026
**Context:** Slice (raw CDP browser automation) fails on Kasada-protected sites (realestate.com.au, hyatt.com) with HTTP 429 + blank page. ips.js fails to load with `net::ERR_INVALID_ARGUMENT`.

---

## 1. Kasada Architecture Summary

### 1.1 What Kasada Is

Kasada is an Australian anti-bot Web Application Firewall (WAF) used by Ticketmaster, PlayStation, Sony, Foot Locker, Canada Goose, Shein, realestate.com.au, Hyatt, and others. It's the most technically sophisticated enterprise anti-bot system in production as of 2026.

**Key differentiator from Cloudflare/Akamai/DataDome/Imperva/PerimeterX: cryptographic proof-of-work.** Every other system uses fingerprinting + behavioral analysis + optional CAPTCHAs. Kasada adds a mandatory CPU-bound hash-collision puzzle that must be solved continuously throughout a session. No CAPTCHA fallback — you solve the PoW or you get a silent 403/429.

**Source:** ScrapeBadger Complete 2026 Guide, Hyper Solutions API Documentation, 2Captcha Kasada Deep Dive, nixbro/Kasada-Solver

### 1.2 The Five-Layer Detection Pipeline

Every request passes through all layers. Each contributes to a composite trust score. Low score = silent block. No visible challenge is ever presented.

```
Request arrives at Kasada edge
↓
Layer 1: TLS + HTTP/2 fingerprint check
↓ fail → 403 immediately (no challenge offered)
↓ pass
Layer 2: IP reputation check
↓ fail → 403
↓ pass
Layer 3: Cryptographic proof-of-work challenge
(JavaScript executes, solves computation puzzle)
↓ fail → 403 / 429
↓ pass
Layer 4: Browser and JavaScript environment fingerprinting
↓ fail → 403
↓ pass
Layer 5: Behavioral analysis and trust score accumulation
↓ low score → silent degradation or block
↓ sufficient score → x-kpsdk-ct token issued → access granted
```

**Source:** ScrapeBadger, scrapfly.io, ZenRows, Hyper Solutions docs

### 1.3 Layer 1: TLS Fingerprinting (JA3/JA4)

- Kasada checks TLS cipher suite ordering, TLS version (1.2/1.3), supported extensions, ALPN, and HTTP/2 SETTINGS frame ordering
- Python `requests` library fails immediately: HTTP/1.1 only, detectable JA3 hash, no HTTP/2
- Chromium's TLS fingerprint is generally trusted by Kasada **if it's a recent version** (Chrome 145+)
- The JA3/JA4 hash from real Chrome differs from headless-Chrome-defaults in some configurations
- **Key insight:** Using `channel=chrome` (system installed Google Chrome) produces a TLS fingerprint indistinguishable from real users. Bundled Chromium may differ subtly.
- **curl_cffi** with `impersonate="chrome"` passes Layer 1 TLS checks but can't execute JavaScript, so it fails at Layer 3

**Source:** Ian Paterson anti-detect browser benchmark 2026, ScrapeBadger, scrapfly.io

### 1.4 Layer 2: IP Reputation

- Kasada maintains **network-wide IP intelligence** shared across all customers
- IP types ranked by trust: Mobile > Residential > Datacenter
- Datacenter IPs (AWS, DigitalOcean, Google Cloud) carry immediate negative trust scores
- IPs flagged on one Kasada-protected site carry degraded reputation everywhere else
- Residential proxies help but don't solve the JS challenge layer — the TLS/HTTP2/fingerprint signals still originate from the actual host, not the proxy

**Source:** ZenRows, ScrapeBadger, 2Captcha

### 1.5 Layer 3: The Cryptographic Proof-of-Work (Kasada's Defining Feature)

This is what separates Kasada from every other system.

**How it works:**
1. Kasada injects `ips.js` (also called `p.js` on some deployments) into the page
2. This script fetches a unique cryptographic puzzle from Kasada servers
3. The client's CPU must solve a hash-collision problem (similar to crypto mining)
4. The solution is encoded into the `x-kpsdk-cd` (Client Data) token
5. The server verifies the solution in microseconds

**Token system:**
- **x-kpsdk-ct** (Client Token): Expensive to generate, reusable, lasts ~30 minutes. Contains client telemetry/fingerprint data.
- **x-kpsdk-cd** (Client Data): Per-request, single-use. Contains proof-of-work solution. Must be freshly generated for each protected request.
- **x-kpsdk-h**: HMAC signature binding CT and CD together. Prevents token mixing/tampering.
- **x-kpsdk-r**: Unique request ID (anti-replay).
- **x-kpsdk-v**: SDK version identifier.
- **x-kpsdk-fc**: Feature configuration (from `/mfc` endpoint on some sites).
- **x-kpsdk-st**: Timestamp for PoW generation.
- **x-kpsdk-im**: Implementation marker (encoded in the ips.js query string).

**Token lifecycle:**
- CT: Generated on first page load. Contains fingerprint data. Good for ~30 minutes. Reusable across requests.
- CD: Unique per request. Contains timestamp + challenge responses. Single-use. Must be <5 seconds old.
- HMAC signature proves: CT and CD from same session, no tampering, request is genuine.
- **CRITICAL:** You cannot reuse CD tokens. Each protected request needs a fresh CD.
- Token expiry: 60–180 seconds (shortest in the industry — Cloudflare is hours, Akamai 30-120 min)

**Source:** nixbro/Kasada-Solver, Hyper Solutions docs, ScrapeBadger, 2Captcha

### 1.6 The Challenge Flow (Technical)

The complete HTTP flow for Kasada challenge resolution:

1. **Browser visits protected site** → May get initial access or immediate 429
2. **Background request to `/fp`** (fingerprint endpoint) → Returns 429 with challenge HTML containing `<script>` tag pointing to `ips.js`
3. **Browser fetches `ips.js`** from path like `/UUID/UUID/ips.js?tkrm_alpekz_s1.3=...&x-kpsdk-im=...`
4. **ips.js executes** → Collects device telemetry (WebGL, canvas, CPU, navigator properties), solves PoW puzzle
5. **POST to `/tl`** endpoint with decoded payload → Returns 200 with `x-kpsdk-ct`, `x-kpsdk-st`, and Kasada cookies
6. **Optional GET to `/mfc`** (feature configuration) → Returns `x-kpsdk-fc` and `x-kpsdk-h`
7. **Protected requests** now include: Kasada cookies + `x-kpsdk-ct` header + `x-kpsdk-cd` header (fresh per-request PoW)

**Source:** Hyper Solutions API documentation (the most detailed technical source available)

### 1.7 Layer 4: JavaScript Environment Fingerprinting (ips.js / p.js)

Kasada's `ips.js` (called `p.js` on some sites) is a **polymorphic virtual machine**:

**Obfuscation techniques:**
- **VM Virtualization:** Core logic compiled to custom bytecode, executed by embedded VM
- **String Encryption:** All strings encrypted, decrypted in memory milliseconds before execution
- **Control Flow Flattening:** Linear code dismantled into massive switch statements
- **Dead Code Injection:** Garbage code paths that never execute but waste reverse-engineer time
- **Variable Name Mangling:** All identifiers scrambled to meaningless strings
- **Polymorphic mutation:** Code structure, variable names, and encryption keys change on every load

**What it fingerprints:**
- `navigator.webdriver` — the most basic headless indicator
- Canvas/WebGL rendering — GPU-matched pixel output vs known software-renderer hash
- Hardware details: CPU threads, device memory, platform
- JavaScript runtime details: timing APIs, prototype chain integrity
- Browser info: version, build, vendor
- OS information: platform, architecture
- **Entropy measurements:** Timing-based detection of uniform server hardware environments

**The `net::ERR_INVALID_ARGUMENT` Problem (Slice's Specific Failure):**
The ips.js script fails to load in Slice's headless Chrome configuration. This means:
- The PoW challenge is never received, much less solved
- No `x-kpsdk-*` tokens are generated
- The server returns 429 + blank page (710 bytes for realestate.com.au, 494 bytes for hyatt.com)
- **Root cause hypothesis:** Chrome launch flags (`--disable-web-security`, `--disable-site-isolation-trials`, `--disable-features=IsolateOrigins`) may interfere with how the browser handles the ips.js script URL (which includes complex query parameters with characters that may be blocked by modified security policies)
- **Alternative hypothesis:** The `x-kpsdk-im` parameter in the query string contains URL characters that Chrome headless considers invalid when certain security features are disabled

**Source:** 2Captcha, nixbro/Kasada-Solver, HackerNoon (Pierluigi Vinciguerra), Hyper Solutions docs

### 1.8 Layer 5: Behavioral Analysis and Trust Score

Trust score is continuously re-evaluated and can decrease over time:

**Signals analyzed:**
- **Request cadence:** Machine-regular intervals vs natural browsing pauses
- **Navigation coherence:** Sessions that jump directly to high-value pages flag
- **Interaction completeness:** Real sessions generate mousemove, scroll, focus, blur, resize events
- **Session duration and browsing pattern:** Natural browsing includes reading pauses, occasional extended dwell times
- **Puzzle difficulty escalation:** When Kasada detects suspicious patterns, it issues harder PoW puzzles

**Source:** ScrapeBadger, scrapfly.io, ZenRows

### 1.9 Comparison: Kasada vs Other Anti-Bot Systems

| System | Hardest Layer | Token Expiry | No-CAPTCHA | Proof-of-Work |
|---|---|---|---|---|
| **Cloudflare** | TLS + JS challenge | Hours | Standard tier: no | No |
| **Akamai** | sensor_data obfuscation | 30–120 min | Yes | No |
| **DataDome** | Behavioral ML | Session | Yes | No |
| **Imperva** | reese84 + 700 dimensions | 15–120 min | Sometimes | No |
| **PerimeterX** | Biometric + Code Defender | ~60 seconds | Yes | No |
| **Kasada** | **Cryptographic PoW** | **60–180 seconds** | **Yes (always)** | **Yes** |

Kasada's combination of shortest token expiry, mandatory no-CAPTCHA mode, and cryptographic proof-of-work makes it objectively the hardest enterprise anti-bot system to bypass in 2026.

**Source:** ScrapeBadger

---

## 2. Bypass Approaches — Ranked by Feasibility for Slice

### 2.1 HIGHEST PRIORITY: Fix ips.js Loading Failure

**What:** The `net::ERR_INVALID_ARGUMENT` error when Chrome tries to load ips.js.

**Why this is the root cause:** ips.js never loads → PoW challenge never starts → no tokens generated → 429. Everything else is irrelevant until this is fixed.

**Investigation path:**
1. **Remove/disable problematic Chrome flags.** The prime suspects:
   - `--disable-web-security` — This flag fundamentally alters CORS and network behavior. It may cause Chrome to reject the ips.js URL (which loads from a UUID-prefixed path with complex query parameters).
   - `--disable-site-isolation-trials` — May interfere with how scripts are loaded in isolated origins.
   - `--disable-features=IsolateOrigins,site-per-process` — May affect cross-origin script loading from Kasada's CDN-style paths.
2. **Test with minimal flags:** Start with only `--headless=new`, `--no-sandbox`, `--disable-gpu`, and re-add flags incrementally to identify which one breaks ips.js.
3. **Check the ips.js URL for encoding issues:** The query parameter `x-kpsdk-im` contains base64-like encoded data. If Chrome is decoding this in a way that conflicts with flag-modified network policies, the request may be rejected.
4. **Use `Fetch.enable` to intercept and manually allow the ips.js request** if a specific flag is the culprit but needed for other stealth.

**Difficulty:** Easy-Medium
**Impact:** Critical — unblocks the entire pipeline

### 2.2 HIGH PRIORITY: Ensure Real Chrome TLS Fingerprint

**What:** Use system Chrome or a recent Chromium build (145+) so the JA3/JA4 fingerprint matches real browsers.

**Why:** Layer 1 check — fail here and you never get to the PoW challenge. Slice already uses standalone Chromium via `npx playwright install chromium`, which is good. But verify the version and ensure no flags are modifying TLS behavior.

**Specific actions:**
- Verify Chromium version is 145+ (check `slice/browser.py` for how the binary is resolved)
- Remove any flags that affect network stack: `--disable-features=NetworkService,NetworkServiceInProcess` may be worth testing without
- Consider using system-installed Google Chrome instead of Playwright's Chromium for a more authentic TLS fingerprint (nodriver's approach)
- The `--enable-features=NetworkService,NetworkServiceInProcess` flag should be tested: does it help or hurt?

**Difficulty:** Easy
**Impact:** High — prerequisite for everything else

### 2.3 HIGH PRIORITY: Session Warming

**What:** Visit homepage → intermediary pages → target page with realistic delays, rather than jumping directly to the target.

**Why:** Kasada's behavioral analysis (Layer 5) scores "cold" sessions on high-value pages very low. StackOverflow, Glassdoor, and similar gated pages reject cold sessions. Multiple sources (ScrapeBadger, scrapfly.io, HackerNoon) confirm this is mandatory for consistent success.

**Implementation for Slice:**
```python
# Pseudo-code for Slice's StealthBrowser
await page.goto("https://www.realestate.com.au/")  # homepage
await asyncio.sleep(random.uniform(2, 4))
await page.goto("https://www.realestate.com.au/buy/")  # intermediary
await asyncio.sleep(random.uniform(1, 3))
await page.goto(target_url)  # actual target
```

**Difficulty:** Easy
**Impact:** High — can be the difference between 429 and successful page load

### 2.4 MEDIUM PRIORITY: Continuous Token Refresh / Re-Challenge Handling

**What:** After initial PoW is solved, monitor for token expiry and re-solve automatically.

**Why:** Tokens expire in 60–180 seconds. A scraper that makes one request and stops is fine. A scraper that makes multiple requests over 2+ minutes will need to re-solve.

**Implementation approach:**
- After first successful page load, check response headers for `x-kpsdk-ct`
- Track token age; refresh before 90 seconds
- On 429 response, trigger re-challenge (reload page, let ips.js solve PoW again)
- Mimic the KasadaSession class from the ScrapeBadger guide

**Difficulty:** Medium
**Impact:** Medium-High — necessary for any multi-page scraping

### 2.5 MEDIUM PRIORITY: Residential Proxies

**What:** Use residential or mobile proxies instead of datacenter IPs.

**Why:** Layer 2 IP reputation. Datacenter IPs start with negative trust scores. Even with perfect JS/TLS fingerprinting, a datacenter IP on a high-security Kasada deployment (Ticketmaster, realestate.com.au) will likely be blocked. Slice already has BrightData/Oxylabs proxy support — this should be used for Kasada targets.

**Difficulty:** Easy (already implemented in Slice)
**Impact:** Medium — improves baseline trust score, but won't help if ips.js never loads

### 2.6 MEDIUM PRIORITY: Timing/Entropy Variance

**What:** Headless Chrome on uniform server hardware produces timing distributions that don't match any real device.

**Why:** Kasada's Layer 4 includes "entropy measurements" — timing-based detection that identifies uniform server environments. nodriver succeeds on targets where Playwright forks fail specifically because it avoids certain detectable timing patterns.

**Mitigation options:**
- Run in headed mode (requires Xvfb on Linux) for Kasada targets
- Introduce system-level noise (background CPU load) to create natural timing variance
- Add variable delays to all CDP operations
- Use real Chrome rather than Chromium (nodriver's `channel=chrome` approach)
- Consider using `asyncio.sleep(random.uniform(min, max))` between CDP commands to break uniform timing patterns

**Difficulty:** Hard
**Impact:** Medium — matters for high-security deployments like Ticketmaster

### 2.7 LOW PRIORITY: Reverse-Engineer ips.js / Token Generation

**What:** De-virtualize Kasada's polymorphic JavaScript VM to generate `x-kpsdk-*` tokens without a browser.

**Why NOT recommended:**
- ips.js is a polymorphic VM with code that changes on every load
- Exploit scripts have "incredibly short lifespan" — what works in the morning may fail by evening
- Requires 24/7 maintenance
- The only dedicated solver (kpsdk-solver by 0x6a69616e) was **archived June 2025**
- Commercial solver APIs (Hyper Solutions, 2Captcha) exist but cost money
- Letting real Chrome execute the challenge is the practical approach

**Difficulty:** Infeasible for a solo/small-team project
**Impact:** Would be highest if achievable, but the maintenance burden makes it impractical

### 2.8 LOW PRIORITY: Switch to Firefox-Based Engine

**What:** Use Firefox (via Camoufox or Playwright-Firefox) instead of Chrome for Kasada targets.

**Why:** Most anti-bot systems focus detection on Chrome. Kasada's Chrome-specific detection is sophisticated. Firefox has a different TLS fingerprint (different cipher suite order) and different JS runtime characteristics. Camoufox specifically handles Kasada (Canada Goose test: ✅ passed). However, this means abandoning Slice's Chrome-CDP architecture for Kasada targets.

**Difficulty:** Hard (architecture change)
**Impact:** Medium — would work but diverges from Slice's core design

---

## 3. What Open-Source Tools Handle Kasada

### 3.1 Verified Working (tested against Kasada in 2025-2026)

**nodriver** (Python, AGPL-3.0, free)
- Best open-source option for Kasada
- Drives Chrome directly via CDP WebSocket — no Playwright/Selenium shim
- **Benchmark results:** 28/31 targets OK, 0 blocked (Ian Paterson, July 2026)
- The **only** browser through Canadian Insider (a strict Cloudflare+Kasada-like gate)
- Zendriver fork is more actively maintained but same approach
- **Relevant to Slice:** This is the closest open-source equivalent to Slice's architecture (raw CDP). If nodriver works and Slice doesn't, the difference is the Chrome launch configuration and CDP command sequencing.
- **Source:** github.com/ultrafunkamsterdam/nodriver, Ian Paterson benchmark

**Patchright** (Python, Apache-2.0, free)
- Playwright fork that patches CDP-leak signals
- **Kasada test:** Canada Goose ✅ passed (HackerNoon, July 2025)
- Uses `channel=chrome` to drive system Chrome for real TLS fingerprint
- **Benchmark:** 25/31 OK, 3 blocked
- **Source:** github.com/Kaliiiiiiiiii-Vinyzu/patchright-python, HackerNoon

**Camoufox** (Python, MPL-2.0, free)
- Firefox-based anti-detect browser
- **Kasada test:** Canada Goose ✅ passed (HackerNoon, July 2025)
- **Benchmark:** 25/31 OK, 3 blocked. Fails on dev.to (Firefox TLS quirk) but wins on Google Search where Chromium forks fail.
- Humanized mouse movements, forged fingerprints included
- **Source:** github.com/daijro/camoufox, HackerNoon

**Zendriver** (Python, nodriver fork, free)
- More actively maintained fork of nodriver
- **Kasada test:** Canada Goose ✅ passed (HackerNoon, July 2025)
- **Source:** github.com/stephanlensky/zendriver, HackerNoon

### 3.2 Not Working / Not Recommended

**kpsdk-solver** (JavaScript, MIT, free)
- Playwright-based dedicated Kasada solver
- **ARCHIVED June 2025** — no longer maintained
- Limitations: only compatible with Playwright; fails on Chromium (Firefox preferred); fails on most Linux (Windows preferred)
- **Source:** github.com/0x6a69616e/kpsdk-solver

**rebrowser-playwright** (Python, unlicensed, free)
- Playwright fork with CDP-leak patches
- Last code commit: September 2024
- **Benchmark:** Identical to vanilla Playwright (24/31 OK, 5 blocked)
- **Source:** Ian Paterson benchmark

**Standard Playwright/Selenium**
- Detected immediately by Kasada
- **Kasada test:** Canada Goose ❌ blank page (HackerNoon)
- Standard headless Chrome is the most detectable configuration

### 3.3 Commercial / API Solutions

- **ScrapeBadger** Kasada bypass: Handles all 5 layers. Infrastructure-level PoW execution.
- **Scrapfly** ASP (Anti-Scraping Protection): `asp=true` parameter handles Kasada automatically.
- **ZenRows** Universal Scraper: Handles Kasada via `premium_proxy=true` + `js_render=true`.
- **Hyper Solutions SDK** (Go/Python/JS): API-based Kasada solver. Handles the full `/fp` → `/tl` → PoW generation flow. Most detailed technical documentation available.
- **2Captcha** Kasada solver: B2B API for generating `x-kpsdk-*` tokens. Uses ML models + cluster computing.

---

## 4. What Makes Kasada Different from What Slice Already Handles

### What Slice Already Does (works on 9/10 sites)
| Capability | Slice Implementation | Kasada Relevance |
|---|---|---|
| navigator.webdriver removal | navigator.py — delete from prototype, getter returning undefined | Layer 4 — necessary, done ✓ |
| WebGL vendor spoofing | webgl.py — hooks getParameter for UNMASKED_VENDOR/RENDERER | Layer 4 — necessary, done ✓ |
| Canvas noise | canvas.py — ±2 per-pixel noise, per-session seed | Layer 4 — necessary, done ✓ |
| AudioContext noise | audio.py — ±0.001 noise on getFloatFrequencyData | Layer 4 — necessary, done ✓ |
| Font spoofing | fonts.py — OS-specific font lists, document.fonts.check override | Layer 4 — necessary, done ✓ |
| Screen/window spoofing | screen.py — dimensions, DPR, colorDepth | Layer 4 — necessary, done ✓ |
| Timezone/locale | timezone.py — Date.getTimezoneOffset, Intl.DateTimeFormat | Layer 4 — necessary, done ✓ |
| Chrome runtime spoofing | chrome.py — chrome.runtime, .app, .csi, .loadTimes | Layer 4 — necessary, done ✓ |
| HTTP headers (UA, Sec-CH-UA) | headers.py — CDP Network.setUserAgentOverride | Layer 1/4 — necessary, done ✓ |
| Sec-Fetch-* headers | tls.py — Network.setExtraHTTPHeaders | Layer 1/4 — necessary, done ✓ |
| Human-like behavior | behavior.py — bezier mouse, variable typing, chunked scroll | Layer 5 — necessary, done ✓ |
| Profile consistency | validator.py — 6 cross-signal checks | Layer 4 — necessary, done ✓ |

### What Slice Is Missing for Kasada
| Gap | Why It Matters | Difficulty |
|---|---|---|
| **ips.js loading** — script fails with ERR_INVALID_ARGUMENT | PoW challenge never starts — immediate 429 | Easy-Medium fix |
| **Proof-of-work auto-solving** — no mechanism to let Chrome solve hash puzzles | Kasada's defining feature — without PoW token, no access | Medium (if ips.js loads, Chrome handles this automatically) |
| **Session warming** — cold sessions hit high-value pages directly | Trust score starts low, triggers aggressive filtering | Easy |
| **Continuous token refresh** — no CD/CT lifecycle management | Tokens expire in 60-180s — multi-page scraping fails | Medium |
| **Entropy variance** — uniform timing on server hardware | Detected by Kasada's entropy measurements | Hard |
| **TLS fingerprint verification** — no check that JA3/JA4 matches real Chrome | Layer 1 prerequisite — must pass before PoW is offered | Easy |
| **HTTP/2 SETTINGS frame ordering** — not verified | Layer 1 part of TLS/HTTP2 fingerprint | Easy |

---

## 5. Recommended Implementation Plan (Ordered Steps)

### Phase 1: Fix the ips.js Loading Failure (Critical Path)

**Goal:** Get ips.js to load so the PoW challenge can run.

**Steps:**
1. **Audit Chrome launch flags in `slice/browser.py`.** Create a minimal flag set for Kasada targets:
   ```python
   KASADA_FLAGS = [
       '--headless=new',
       '--no-sandbox',
       '--disable-gpu',
       '--disable-dev-shm-usage',
       '--disable-blink-features=AutomationControlled',
       '--use-gl=swiftshader',
       '--window-size=1920,1080',
       # Note: intentionally omitting --disable-web-security, 
       # --disable-site-isolation-trials, --disable-features=IsolateOrigins
   ]
   ```
2. **Test with the reduced flag set** against realestate.com.au and hyatt.com
3. **If ips.js still fails:** Use `Fetch.enable` to intercept the script request and manually pass it through with correct headers
4. **If ips.js loads:** Verify that the PoW challenge completes (check for `x-kpsdk-ct` in response headers, check that response body is > 1000 bytes)
5. **Bisect the flag set** to identify the specific flag(s) that break ips.js

**Success criteria:** ips.js loads, PoW challenge completes, page renders with real content (not blank/429)

### Phase 2: Verify TLS/HTTP2 Fingerprint

**Goal:** Ensure Layer 1 passes so PoW is even offered.

**Steps:**
1. Verify Chromium version used by Slice is 145+
2. Test with and without `--enable-features=NetworkService,NetworkServiceInProcess` (this flag modifies network stack behavior)
3. Use a JA3 fingerprint checking tool on the connection to verify it matches real Chrome
4. If needed, switch to system Chrome binary instead of Playwright's bundled Chromium

### Phase 3: Implement Session Warming

**Goal:** Pass Layer 5 behavioral analysis.

**Steps:**
1. Before navigating to a Kasada-protected target URL, visit:
   - The site's homepage → wait 2-4 seconds
   - An intermediary page (category/search) → wait 1-3 seconds
2. Extract the domain from the target URL and auto-generate the warm-up sequence
3. Make this configurable: `StealthBrowser(kasada_warmup=True)`

### Phase 4: Implement Continuous Re-Challenge

**Goal:** Handle token expiry for multi-page scraping.

**Steps:**
1. After the initial page load, store the `x-kpsdk-ct` token and timestamp
2. Before each subsequent request, check if token is older than 90 seconds
3. If expired: trigger page reload on the same domain to get fresh tokens
4. On 429 response: automatically trigger re-challenge (reload page)
5. Add a `KasadaSession` class or flag to `StealthBrowser` that manages this lifecycle

### Phase 5: Enable Residential Proxies for Kasada Targets

**Goal:** Pass Layer 2 IP reputation.

**Steps:**
1. Require or strongly recommend residential proxies for Kasada-protected targets
2. Use Slice's existing BrightData/Oxylabs proxy integration
3. Sticky sessions (same domain → same proxy) are important for Kasada's session tracking

### Phase 6: (If Still Needed) Advanced Stealth — Entropy & Timing

**Goal:** Pass advanced entropy measurements on high-security deployments.

**Steps:**
1. Add variable delays (5-50ms Gaussian jitter) between CDP commands
2. Consider running headed Xvfb mode for Kasada targets (more realistic GPU timing)
3. Introduce background system noise via `stress` or `cpulimit` to create natural timing variance
4. Test against a known aggressive Kasada site (Ticketmaster) to validate

---

## 6. Feasibility Assessment

| Aspect | Verdict |
|---|---|
| **Can Slice bypass Kasada?** | **Yes, likely achievable.** The architecture (raw CDP, no WebDriver, comprehensive stealth injection) is fundamentally the right approach. nodriver — the closest open-source equivalent — succeeds on Kasada. Slice's failure is a configuration bug (Chrome flags breaking ips.js), not an architectural limitation. |
| **Difficulty of the fix** | **Easy-Medium.** The ips.js loading problem is likely a flag configuration issue. Session warming and token refresh are straightforward additions. |
| **Will it work on all Kasada sites?** | **Probably not.** High-security deployments (Ticketmaster) use aggressive configurations with dynamic puzzle difficulty escalation and entropy measurements that detect uniform server hardware. Residential proxies may be mandatory for those. |
| **Is external help needed?** | **Residential proxies: Strongly recommended.** Even with perfect stealth, datacenter IPs on Kasada will have low trust scores. Slice's existing BrightData/Oxylabs integration covers this. |
| **Time to bypass** | **Days, not weeks.** The core issue (ips.js loading) is likely solvable by removing problematic Chrome flags. The rest is incremental. |
| **Maintenance burden** | **Medium.** Kasada mutates ips.js continuously. The bypass approach (letting real Chrome execute the challenge) is inherently resilient to JS changes. But Chrome version updates and Kasada configuration changes will require periodic testing. |

---

## 7. Source Links

### Kasada Architecture & Internals
- **ScrapeBadger Complete 2026 Guide:** https://scrapebadger.com/blog/how-to-bypass-kasada-anti-bot-complete-2026-guide
- **Scrapfly Kasada Bypass Guide:** https://scrapfly.io/blog/posts/how-to-bypass-kasada-anti-scraping-waf
- **2Captcha Kasada Deep Dive:** https://2captcha.com/h/kasada-bypass
- **ZenRows Kasada Bypass:** https://www.zenrows.com/blog/kasada-bypass
- **Hyper Solutions Kasada API Docs (most detailed technical source):** https://docs.hypersolutions.co/k4sada/flow-2-fingerprint-endpoint
- **HackerNoon Open-Source Kasada Bypass:** https://hackernoon.com/kasada-anti-bot-bypass-techniques-save-money-with-these-open-source-solutions

### Token/Header System
- **nixbro/Kasada-Solver (High-Level Overview):** https://github.com/nixbro/Kasada-Solver
- **kpsdk-solver (archived Playwright solver):** https://github.com/0x6a69616e/kpsdk-solver
- **Humphryyy/Kasada-Deobfuscated:** https://github.com/Humphryyy/Kasada-Deobfuscated
- **Pr0t0ns/Kasada-Reverse:** https://github.com/Pr0t0ns/Kasada-Reverse

### Browser Benchmark Data
- **Ian Paterson Anti-Detect Browser Benchmark 2026:** https://ianlpaterson.com/blog/anti-detect-browser-benchmark-patchright-nodriver-curl-cffi/
- **techinz/browsers-benchmark (354★):** https://github.com/techinz/browsers-benchmark

### Working Open-Source Tools
- **nodriver:** https://github.com/ultrafunkamsterdam/nodriver
- **Zendriver (nodriver fork):** https://github.com/stephanlensky/zendriver
- **Patchright:** https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python
- **Camoufox:** https://github.com/daijro/camoufox

### Commercial Bypass Services
- **ScrapeBadger Kasada Bypass:** https://scrapebadger.com/kasada-bypass
- **Hyper Solutions Kasada API:** https://hypersolutions.co/products/kasada
- **CaptchaSonic Kasada Solver:** https://captchasonic.com/en/products/kasada

### Reddit Discussions
- **r/webscraping: Bypass Kasada:** https://www.reddit.com/r/webscraping/comments/1evi43c/bypass_kasada/
- **r/thewebscrapingclub: How to scrape Kasada-protected websites:** https://www.reddit.com/r/thewebscrapingclub/comments/11pg2vq/how_to_scrape_kasadaprotected_websites/

---

## Appendix: Kasada Identification Checklist

When visiting a site, Kasada is present if you see:

✓ Response headers containing `x-kpsdk-*` (specifically: ct, cd, r, h, v)
✓ Background requests to paths matching `/UUID/UUID/fp` or `/UUID/UUID/tl`
✓ Script loads from paths matching `/UUID/UUID/ips.js` or `/UUID/UUID/p.js`
✓ 403/429 responses with NO visible challenge page (no CAPTCHA, no "verify you're human")
✓ The page loads initially with 429, then reloads normally (Kasada behavior — PoW solved)
✓ Wappalyzer reports "Kasada" in the tech stack
