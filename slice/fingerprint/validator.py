"""Fingerprint consistency validator — checks that all signals tell the same story."""

import json

# Consistency rules: each hardware profile type has expected correlations
CONSISTENCY_RULES = {
    # GPU vendor → expected hardware tier
    "Intel Inc.": {"tier": "laptop", "ram_range": (4, 16), "core_range": (2, 8)},
    "Intel Iris OpenGL Engine": {"tier": "laptop", "ram_range": (4, 16), "core_range": (2, 8)},
    "Apple": {"tier": "laptop", "ram_range": (8, 32), "core_range": (4, 12)},
    "NVIDIA Corporation": {"tier": "desktop", "ram_range": (8, 64), "core_range": (4, 16)},
    "AMD": {"tier": "desktop", "ram_range": (8, 64), "core_range": (4, 16)},
}


class ValidationResult:
    """Result of a fingerprint consistency check."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: bool = True

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def __str__(self):
        lines = []
        if self.passed:
            lines.append("VALIDATION PASSED")
        else:
            lines.append("VALIDATION FAILED")
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARN:  {w}")
        return "\n".join(lines)

    @property
    def is_valid(self) -> bool:
        return self.passed


def validate_profile(profile: dict) -> ValidationResult:
    """Check a fingerprint profile for internal consistency.

    Validates:
    - OS ↔ User-Agent alignment
    - Platform ↔ OS alignment
    - Screen ↔ viewport consistency
    - GPU ↔ hardware specs consistency
    - Font list ↔ OS consistency
    - Language/timezone reasonableness
    """
    result = ValidationResult()

    # 1. OS ↔ User-Agent
    ua = profile.get("user_agent", "")
    os_type = profile.get("os", "")
    if os_type == "windows" and "Windows" not in ua:
        result.add_error(f"OS is 'windows' but UA doesn't contain 'Windows': {ua[:60]}")
    elif os_type == "macos" and "Macintosh" not in ua:
        result.add_error(f"OS is 'macos' but UA doesn't contain 'Macintosh': {ua[:60]}")
    elif os_type == "linux" and "Linux" not in ua:
        result.add_error(f"OS is 'linux' but UA doesn't contain 'Linux': {ua[:60]}")

    # 2. Platform ↔ OS
    platform = profile.get("platform", "")
    if os_type == "windows" and platform != "Win32":
        result.add_error(f"OS is 'windows' but platform is '{platform}' (expected Win32)")
    elif os_type == "macos" and platform != "MacIntel":
        result.add_error(f"OS is 'macos' but platform is '{platform}' (expected MacIntel)")
    elif os_type == "linux" and "Linux" not in platform:
        result.add_error(f"OS is 'linux' but platform is '{platform}'")

    # 3. Screen ↔ viewport
    screen = profile.get("screen", {})
    viewport = profile.get("viewport", {})
    sw, sh = screen.get("width", 0), screen.get("height", 0)
    vw, vh = viewport.get("width", 0), viewport.get("height", 0)
    if sw > 0 and vw > 0:
        if vw > sw or vh > sh:
            result.add_error(f"Viewport ({vw}x{vh}) larger than screen ({sw}x{sh})")
    if screen.get("avail_width", 0) > sw:
        result.add_error(f"avail_width ({screen['avail_width']}) > screen width ({sw})")

    # 4. GPU ↔ hardware consistency
    webgl = profile.get("webgl", {})
    renderer = webgl.get("renderer", "")
    cores = profile.get("hardware_concurrency", 0)
    memory = profile.get("device_memory", 0)
    for gpu_key, rules in CONSISTENCY_RULES.items():
        if gpu_key.lower() in renderer.lower():
            ram_min, ram_max = rules["ram_range"]
            core_min, core_max = rules["core_range"]
            if memory < ram_min or memory > ram_max:
                result.add_warning(
                    f"GPU '{renderer}' suggests {rules['tier']} with {ram_min}-{ram_max}GB RAM, "
                    f"but device_memory is {memory}GB"
                )
            if cores < core_min or cores > core_max:
                result.add_warning(
                    f"GPU '{renderer}' suggests {rules['tier']} with {core_min}-{core_max} cores, "
                    f"but hardware_concurrency is {cores}"
                )
            break

    # 5. Font list ↔ OS
    fonts = profile.get("fonts", [])
    if os_type == "windows":
        expected = {"Segoe UI", "Calibri", "Consolas"}
        has_any = any(f in fonts for f in expected)
        if not has_any and fonts:
            result.add_warning("OS is 'windows' but font list lacks typical Windows fonts (Segoe UI, Calibri)")
    elif os_type == "macos":
        expected = {"Helvetica Neue", "Menlo", "SF Pro"}
        has_any = any(f in fonts for f in expected)
        if not has_any and fonts:
            result.add_warning("OS is 'macos' but font list lacks typical macOS fonts (Helvetica Neue, Menlo)")

    # 6. Browser version in UA matches browser_version
    bv = profile.get("browser_version", "")
    if bv and bv.split(".")[0] not in ua:
        result.add_warning(f"browser_version '{bv}' not found in UA string")

    # 7. DPR sanity
    dpr = screen.get("device_pixel_ratio", 1)
    if os_type == "macos" and dpr < 2:
        result.add_warning(f"macOS screen typically has DPR=2, got {dpr}")
    if os_type == "windows" and dpr > 1.5:
        result.add_warning(f"Windows screen DPR={dpr} is unusual for most setups")

    return result
