"""Font list generation for fingerprint consistency."""

# Common Windows fonts (Chrome on Windows 10/11)
WINDOWS_FONTS = [
    "Arial", "Arial Black", "Calibri", "Cambria", "Candara",
    "Comic Sans MS", "Consolas", "Constantia", "Corbel",
    "Courier New", "Georgia", "Impact", "Lucida Console",
    "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
    "Segoe UI Light", "Segoe UI Semibold", "Tahoma",
    "Times New Roman", "Trebuchet MS", "Verdana",
]

# Common macOS fonts
MACOS_FONTS = [
    "American Typewriter", "Apple Chancery", "Arial", "Arial Black",
    "Avenir", "Avenir Next", "Baskerville", "Big Caslon",
    "Brush Script MT", "Chalkboard", "Cochin", "Comic Sans MS",
    "Copperplate", "Courier New", "Didot", "Futura",
    "Geneva", "Georgia", "Gill Sans", "Helvetica",
    "Helvetica Neue", "Hoefler Text", "Impact", "Lucida Grande",
    "Marker Felt", "Menlo", "Monaco", "Optima",
    "Palatino", "Papyrus", "Phosphate", "Rockwell",
    "SF Pro", "Skia", "Times New Roman", "Trebuchet MS", "Verdana",
]

# Common Linux fonts
LINUX_FONTS = [
    "DejaVu Sans", "DejaVu Sans Mono", "DejaVu Serif",
    "FreeMono", "FreeSans", "FreeSerif",
    "Liberation Mono", "Liberation Sans", "Liberation Serif",
    "Nimbus Mono L", "Nimbus Roman No9 L", "Nimbus Sans L",
    "Ubuntu", "Ubuntu Condensed", "Ubuntu Mono",
    "Droid Sans", "Droid Serif", "Droid Sans Mono",
    "Arial", "Courier New", "Georgia", "Times New Roman",
    "Trebuchet MS", "Verdana",
]


def get_fonts_for_os(os_type: str = "windows") -> list[str]:
    """Get the font list matching the target OS."""
    if os_type == "windows":
        return WINDOWS_FONTS
    elif os_type == "macos":
        return MACOS_FONTS
    else:
        return LINUX_FONTS


def make_font_enumeration_script(fonts: list[str]) -> str:
    """Generate a script that spoofs font enumeration results."""
    fonts_js = str(fonts)
    return f"""
// Intercept font enumeration via measuring text width
// Fonts that are 'available' return slightly different widths
const _fontList = {fonts_js};
const _offsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
const _getComputedStyle = window.getComputedStyle;

// Override document.fonts.check to report our font list
if (document.fonts && document.fonts.check) {{
    const _check = document.fonts.check.bind(document.fonts);
    document.fonts.check = function(font) {{
        const family = font.split(' ').pop().replace(/['"]/g, '');
        if (_fontList.some(f => f.toLowerCase() === family.toLowerCase())) {{
            return true;
        }}
        return _check(font);
    }};
}}
"""


def get_script(profile: dict = None) -> str:
    if profile is None:
        profile = {}
    fonts = profile.get("fonts", get_fonts_for_os(profile.get("os", "windows")))
    return make_font_enumeration_script(fonts)
