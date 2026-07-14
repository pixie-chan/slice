# Bypassing the Final Layer — Residential Proxies & 2Captcha

## Residential Proxies

### What
A residential proxy routes traffic through real residential IPs (home internet connections). Datacenter IPs (AWS, DigitalOcean, etc.) are blacklisted by advanced bot protection — Kasada, DataDome, Akamai all check IP reputation as Layer 2.

### Why Needed
Even with perfect fingerprint stealth, a datacenter IP triggers immediate distrust:
- Kasada: IP reputation is Layer 2 — fails = 429/403, no challenge offered
- DataDome: flags known hosting providers
- Akamai: IP reputation scoring across their entire customer network

### How to Get
| Provider | Price | Best For |
|:--|:--|:--|
| BrightData | ~$5-15/GB | Production scraping, largest IP pool |
| Oxylabs | ~$8-12/GB | Enterprise, good rotation |
| Smartproxy | ~$4-8/GB | Budget-friendly |
| IPRoyal | ~$3-7/GB | Decent quality, cheaper |

### Slice Integration
Slice has built-in proxy support:
```bash
# SOCKS5 proxy
slice scrape --url "https://kasada-site.com" --proxy "socks5://user:pass@proxy:port"

# HTTP proxy
slice scrape --url "https://kasada-site.com" --proxy "http://user:pass@proxy:port"
```

For Kasada: sticky sessions are important — same domain → same proxy IP.

---

## 2Captcha API Key

### What
A CAPTCHA-solving service. You send the challenge (Turnstile, reCAPTCHA, hCaptcha), they solve it (AI + human workers), send back the solution token. Slice then injects that token into the browser.

### Why Needed
Cloudflare Turnstile on NowSecure and other sites requires solving a challenge that headless Chrome can't solve alone. Slice detects the Turnstile (`captcha/solver.py`) and has the API wrapper (`captcha/api.py`), but needs a key to call 2Captcha.

### How to Get
1. Go to https://2captcha.com
2. Sign up (email + password)
3. Deposit $1-2 minimum (supports crypto, cards)
4. Go to **Dashboard → API Keys**
5. Copy the key (looks like `a1b2c3d4e5f6...`)

### Slice Integration
```bash
# With 2Captcha key for auto-solving
slice scrape --url "https://nowsecure.nl" --solve-captcha --api-key YOUR_2CAPTCHA_KEY
```

Cost: ~$0.50-3 per 1000 CAPTCHAs depending on type.

---

## Cost to Get Started
- Residential proxy: ~$5-10 (one-time deposit, pay per GB used)
- 2Captcha: ~$1-2 (deposited, pay per solve)
- **Total: ~$6-12** to unlock Kasada + Turnstile bypass
