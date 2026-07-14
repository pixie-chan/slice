"""Fingerprint profile generator — creates consistent browser fingerprint profiles.

All values in a profile must tell the SAME STORY:
- Intel Iris GPU → laptop → 8GB RAM, 4 cores, 1920x1080
- NVIDIA RTX → desktop → 16GB RAM, 8 cores, 2560x1440
- AMD Radeon → varies
"""

import json
import random
import os

# Hardware profile presets — each tells a consistent story
HARDWARE_PROFILES = {
    "windows_chrome_intel": {
        "os": "windows",
        "browser": "chrome",
        "browser_version": "126.0.0.0",
        "platform": "Win32",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "screen": {"width": 1920, "height": 1080, "avail_width": 1920, "avail_height": 1040, "device_pixel_ratio": 1},
        "locale": "en-US",
        "timezone": "America/New_York",
        "languages": ["en-US", "en"],
        "webgl": {"vendor": "Intel Inc.", "renderer": "Intel Iris OpenGL Engine"},
        "hardware_concurrency": 4,
        "device_memory": 8,
        "plugins": ["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
        "fonts": [
            "Arial", "Arial Black", "Calibri", "Cambria", "Candara",
            "Comic Sans MS", "Consolas", "Constantia", "Corbel",
            "Courier New", "Georgia", "Impact", "Lucida Console",
            "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
            "Segoe UI Light", "Segoe UI Semibold", "Tahoma",
            "Times New Roman", "Trebuchet MS", "Verdana",
        ],
        "connection": {"type": "wifi", "effective_type": "4g", "downlink": 10, "rtt": 50},
    },
    "macos_chrome_apple": {
        "os": "macos",
        "browser": "chrome",
        "browser_version": "126.0.0.0",
        "platform": "MacIntel",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "screen": {"width": 1440, "height": 900, "avail_width": 1440, "avail_height": 875, "device_pixel_ratio": 2},
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "languages": ["en-US", "en"],
        "webgl": {"vendor": "Apple", "renderer": "Apple M2"},
        "hardware_concurrency": 8,
        "device_memory": 16,
        "plugins": ["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
        "fonts": [
            "American Typewriter", "Apple Chancery", "Arial", "Arial Black",
            "Avenir", "Avenir Next", "Baskerville", "Big Caslon",
            "Chalkboard", "Cochin", "Comic Sans MS", "Copperplate",
            "Courier New", "Didot", "Futura", "Geneva", "Georgia",
            "Gill Sans", "Helvetica", "Helvetica Neue", "Hoefler Text",
            "Impact", "Lucida Grande", "Menlo", "Monaco", "Optima",
            "Palatino", "SF Pro", "Skia", "Times New Roman",
            "Trebuchet MS", "Verdana",
        ],
        "connection": {"type": "wifi", "effective_type": "4g", "downlink": 20, "rtt": 30},
    },
    "linux_firefox_amd": {
        "os": "linux",
        "browser": "firefox",
        "browser_version": "128.0",
        "platform": "Linux x86_64",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "viewport": {"width": 1920, "height": 1080},
        "screen": {"width": 1920, "height": 1080, "avail_width": 1920, "avail_height": 1052, "device_pixel_ratio": 1},
        "locale": "en-US",
        "timezone": "America/Chicago",
        "languages": ["en-US", "en"],
        "webgl": {"vendor": "AMD", "renderer": "AMD Radeon RX 580"},
        "hardware_concurrency": 8,
        "device_memory": 16,
        "plugins": [],
        "fonts": [
            "DejaVu Sans", "DejaVu Sans Mono", "DejaVu Serif",
            "FreeMono", "FreeSans", "FreeSerif",
            "Liberation Mono", "Liberation Sans", "Liberation Serif",
            "Ubuntu", "Ubuntu Condensed", "Ubuntu Mono",
            "Droid Sans", "Droid Serif", "Arial", "Courier New",
            "Georgia", "Times New Roman", "Verdana",
        ],
        "connection": {"type": "ethernet", "effective_type": "4g", "downlink": 50, "rtt": 20},
    },
    "windows_chrome_nvidia": {
        "os": "windows",
        "browser": "chrome",
        "browser_version": "126.0.0.0",
        "platform": "Win32",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "viewport": {"width": 2560, "height": 1440},
        "screen": {"width": 2560, "height": 1440, "avail_width": 2560, "avail_height": 1400, "device_pixel_ratio": 1},
        "locale": "en-US",
        "timezone": "America/New_York",
        "languages": ["en-US", "en"],
        "webgl": {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 3070/PCIe/SSE2"},
        "hardware_concurrency": 8,
        "device_memory": 16,
        "plugins": ["Chrome PDF Plugin", "Chrome PDF Viewer", "Native Client"],
        "fonts": [
            "Arial", "Arial Black", "Calibri", "Cambria", "Candara",
            "Comic Sans MS", "Consolas", "Constantia", "Corbel",
            "Courier New", "Georgia", "Impact", "Lucida Console",
            "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
            "Segoe UI Light", "Segoe UI Semibold", "Tahoma",
            "Times New Roman", "Trebuchet MS", "Verdana",
        ],
        "connection": {"type": "ethernet", "effective_type": "4g", "downlink": 50, "rtt": 20},
    },
}


def generate_profile(
    os: str = "windows",
    browser: str = "chrome",
    timezone: str = None,
    locale: str = None,
) -> dict:
    """Generate a consistent fingerprint profile.

    Args:
        os: Target OS ("windows", "macos", "linux")
        browser: Target browser ("chrome", "firefox")
        timezone: Override timezone (e.g., "America/Chicago")
        locale: Override locale (e.g., "en-US")

    Returns:
        Complete fingerprint profile dict.
    """
    # Find the best matching preset
    key = f"{os}_{browser}"
    # Try exact match first, then partial
    if key in HARDWARE_PROFILES:
        profile = HARDWARE_PROFILES[key].copy()
    elif os == "windows":
        profile = HARDWARE_PROFILES["windows_chrome_intel"].copy()
    elif os == "macos":
        profile = HARDWARE_PROFILES["macos_chrome_apple"].copy()
    else:
        profile = HARDWARE_PROFILES["linux_firefox_amd"].copy()

    # Override OS/browser if needed
    profile["os"] = os
    profile["browser"] = browser

    if timezone:
        profile["timezone"] = timezone
    if locale:
        profile["locale"] = locale

    return profile


def save_profile(profile: dict, filepath: str) -> None:
    """Save a fingerprint profile to JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)


def load_profile(filepath: str) -> dict:
    """Load a fingerprint profile from JSON."""
    with open(filepath) as f:
        return json.load(f)


def create_preset_profiles() -> None:
    """Generate and save all preset profiles."""
    profiles_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "profiles",
    )
    for name, profile in HARDWARE_PROFILES.items():
        path = os.path.join(profiles_dir, f"{name}.json")
        save_profile(profile, path)
        print(f"Saved: {path}")
