"""Navigator spoofing — plugins, languages, hardwareConcurrency, webdriver removal."""

# JavaScript injection to remove navigator.webdriver and spoof navigator properties.
# All injected via Page.addScriptToEvaluateOnNewDocument at document_start.

REMOVE_WEBDRIVER = """
// Remove navigator.webdriver from the prototype chain
delete Object.getPrototypeOf(navigator).webdriver;
// Belt-and-suspenders: redefine it as undefined
Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {
    get: () => undefined,
    configurable: true
});
"""

FAKE_PLUGINS = """
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const pluginData = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer',
             description: 'Portable Document Format', length: 1},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
             description: '', length: 1},
            {name: 'Native Client', filename: 'internal-nacl-plugin',
             description: '', length: 2}
        ];
        const arr = pluginData.map(p => {
            const plugin = Object.create(Plugin.prototype);
            Object.defineProperties(plugin, {
                name: {get: () => p.name, enumerable: false, configurable: true},
                filename: {get: () => p.filename, enumerable: false, configurable: true},
                description: {get: () => p.description, enumerable: false, configurable: true},
                length: {get: () => p.length, enumerable: false, configurable: true}
            });
            return plugin;
        });
        const arrObj = Object.create(PluginArray.prototype);
        Object.defineProperties(arrObj, {
            length: {get: () => arr.length},
            item: {value: (i) => arr[i] || null},
            namedItem: {value: (n) => arr.find(p => p.name === n) || null},
            refresh: {value: () => {}}
        });
        return arrObj;
    },
    configurable: true
});
"""


def make_fake_languages(languages=None):
    """Generate navigator.languages spoofing script."""
    if languages is None:
        languages = ["en-US", "en"]
    langs_js = str(languages)
    return f"""
Object.defineProperty(Object.getPrototypeOf(navigator), 'languages', {{
    get: () => Object.freeze({langs_js}),
    configurable: true
}});
"""


def make_fake_hardware(concurrency=4, memory=8):
    """Generate hardwareConcurrency and deviceMemory spoofing scripts."""
    return f"""
try {{
    Object.defineProperty(Object.getPrototypeOf(navigator), 'hardwareConcurrency', {{
        get: () => {concurrency},
        configurable: true
    }});
}} catch(e) {{
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {concurrency},
        configurable: true
    }});
}}
try {{
    Object.defineProperty(Object.getPrototypeOf(navigator), 'deviceMemory', {{
        get: () => {memory},
        configurable: true
    }});
}} catch(e) {{
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {memory},
        configurable: true
    }});
}}
"""

FAKE_VENDOR = """
try {
    Object.defineProperty(Object.getPrototypeOf(navigator), 'vendor', {
        get: () => 'Google Inc.',
        configurable: true
    });
} catch(e) {
    Object.defineProperty(navigator, 'vendor', {
        get: () => 'Google Inc.',
        configurable: true
    });
}
"""

FAKE_PLATFORM_WIN = """
Object.defineProperty(Object.getPrototypeOf(navigator), 'platform', {
    get: () => 'Win32',
    configurable: true
});
"""

FAKE_PLATFORM_MAC = """
Object.defineProperty(Object.getPrototypeOf(navigator), 'platform', {
    get: () => 'MacIntel',
    configurable: true
});
"""

FAKE_PLATFORM_LINUX = """
Object.defineProperty(Object.getPrototypeOf(navigator), 'platform', {
    get: () => 'Linux x86_64',
    configurable: true
});
"""


def get_all_scripts(profile: dict = None) -> str:
    """Combine all navigator spoofing into a single script.

    Args:
        profile: Optional fingerprint profile dict with keys like
                 'languages', 'hardware_concurrency', 'device_memory', 'os'.
    """
    if profile is None:
        profile = {}

    scripts = [REMOVE_WEBDRIVER, FAKE_PLUGINS]

    scripts.append(make_fake_languages(profile.get("languages", ["en-US", "en"])))
    scripts.append(make_fake_hardware(
        profile.get("hardware_concurrency", 4),
        profile.get("device_memory", 8),
    ))
    scripts.append(FAKE_VENDOR)

    os_type = profile.get("os", "windows")
    if os_type == "windows":
        scripts.append(FAKE_PLATFORM_WIN)
    elif os_type == "macos":
        scripts.append(FAKE_PLATFORM_MAC)
    else:
        scripts.append(FAKE_PLATFORM_LINUX)

    return "\n".join(scripts)
