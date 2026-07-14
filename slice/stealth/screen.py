"""Screen resolution and window dimension spoofing."""


def make_script(width=1920, height=1080, avail_width=None, avail_height=None, device_pixel_ratio=1):
    """Generate screen dimension spoofing script."""
    if avail_width is None:
        avail_width = width
    if avail_height is None:
        avail_height = height - 40  # taskbar

    return f"""
// Screen properties
Object.defineProperty(screen, 'width', {{get: () => {width}}});
Object.defineProperty(screen, 'height', {{get: () => {height}}});
Object.defineProperty(screen, 'availWidth', {{get: () => {avail_width}}});
Object.defineProperty(screen, 'availHeight', {{get: () => {avail_height}}});
Object.defineProperty(screen, 'colorDepth', {{get: () => 24}});
Object.defineProperty(screen, 'pixelDepth', {{get: () => 24}});
Object.defineProperty(window, 'devicePixelRatio', {{get: () => {device_pixel_ratio}}});

// Window outer dimensions (headless has outer == inner, real browsers differ)
Object.defineProperty(window, 'outerWidth', {{get: () => {width}}});
Object.defineProperty(window, 'outerHeight', {{get: () => {height} + 85}});
Object.defineProperty(window, 'innerWidth', {{get: () => {width} - 16}});
Object.defineProperty(window, 'innerHeight', {{get: () => {height} - 85}});
"""


def get_script(profile: dict = None) -> str:
    if profile is None:
        profile = {}
    screen = profile.get("screen", {})
    viewport = profile.get("viewport", {})
    w = viewport.get("width", screen.get("width", 1920))
    h = viewport.get("height", screen.get("height", 1080))
    return make_script(
        width=w,
        height=h,
        avail_width=screen.get("avail_width", w),
        avail_height=screen.get("avail_height", h - 40),
        device_pixel_ratio=screen.get("device_pixel_ratio", 1),
    )
