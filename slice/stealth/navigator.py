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

// Remove CDP runtime detection markers (if document is available)
(function() {
    try {
        if (typeof document !== 'undefined') {
            const props = ['$cdp', '__$cdp', '__commandLineAPI'];
            for (const prop of props) {
                try {
                    Object.defineProperty(document, prop, {
                        get: () => undefined,
                        set: function() {},
                        configurable: true
                    });
                } catch(e) {}
            }
        }
    } catch(e) {}
})();
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

# navigator.connection — headless Chrome reports rtt=0, downlink=0 (bot giveaway)
FAKE_CONNECTION = """
if (navigator.connection) {
    Object.defineProperties(navigator.connection, {
        'rtt': { get: () => 50, configurable: true },
        'downlink': { get: () => 10, configurable: true },
        'effectiveType': { get: () => '4g', configurable: true },
        'saveData': { get: () => false, configurable: true }
    });
} else {
    // Create fake connection if missing (headless Chrome often lacks it entirely)
    try {
        Object.defineProperty(navigator, 'connection', {
            get: () => Object.create(Object.prototype, {
                'rtt': { get: () => 50 },
                'downlink': { get: () => 10 },
                'effectiveType': { get: () => '4g' },
                'saveData': { get: () => false },
                'type': { get: () => 'wifi' },
                'addEventListener': { value: () => {} },
                'removeEventListener': { value: () => {} },
                'onchange': { value: null, writable: true }
            }),
            configurable: true
        });
    } catch(e) {}
}
"""

# Notification.permission — headless Chrome often returns "denied" or inconsistent values
FAKE_NOTIFICATIONS = """
if (typeof Notification !== 'undefined') {
    try {
        Object.defineProperty(Notification, 'permission', {
            get: () => 'default',
            configurable: true
        });
    } catch(e) {
        // Fallback: might be read-only, that's okay
    }
}
"""

# MediaDevices.enumerateDevices — patch to not reveal headless Chrome's limited devices
FAKE_MEDIA_DEVICES = """
if (typeof MediaDevices !== 'undefined' && MediaDevices.prototype && MediaDevices.prototype.enumerateDevices) {
    const _enumerateDevices = MediaDevices.prototype.enumerateDevices;
    MediaDevices.prototype.enumerateDevices = function() {
        return _enumerateDevices.call(this).then(devices => {
            // If no real devices are available (common in headless), return fake ones
            if (!devices || devices.length === 0 || devices.every(d => d.deviceId === '' || d.deviceId === 'default')) {
                return [
                    {deviceId: 'fake-video-1', kind: 'videoinput', label: 'Integrated Camera (04f2:b6d9)', groupId: 'fake-group-1'},
                    {deviceId: 'fake-audio-1', kind: 'audioinput', label: 'Microphone (Realtek Audio)', groupId: 'fake-group-2'},
                    {deviceId: 'fake-audio-2', kind: 'audiooutput', label: 'Speakers (Realtek Audio)', groupId: 'fake-group-2'},
                ];
            }
            return devices;
        });
    };
}
"""

# Permissions API — query() must return consistent values
FAKE_PERMISSIONS = """
if (typeof Permissions !== 'undefined' && Permissions.prototype && Permissions.prototype.query) {
    const _query = Permissions.prototype.query;
    Permissions.prototype.query = function(desc) {
        if (desc.name === 'notifications' || desc.name === 'clipboard-read' || desc.name === 'clipboard-write' || desc.name === 'midi') {
            return Promise.resolve({state: 'prompt', onchange: null});
        }
        return _query.call(this, desc);
    };
}
"""

# navigator.userAgentData — modern UA detection (Sec-CH-UA)
def make_user_agent_data_script(os_type: str = "windows", browser_version: str = "126.0.0.0") -> str:
    """Generate navigator.userAgentData spoofing to match Client Hints."""
    major = browser_version.split(".")[0]
    platform = "Windows" if os_type == "windows" else ("macOS" if os_type == "macos" else "Linux")
    platform_version = "10.0.0" if os_type == "windows" else "14.0.0"
    return f"""(function() {{
try {{
    const fakeUAD = {{
        brands: [
            {{brand: 'Google Chrome', version: '{major}'}},
            {{brand: 'Chromium', version: '{major}'}},
            {{brand: 'Not=A?Brand', version: '99'}}
        ],
        mobile: false,
        platform: '{platform}',
        getHighEntropyValues: function(hints) {{
            return Promise.resolve({{
                architecture: 'x86',
                bitness: '64',
                fullVersionList: [
                    {{brand: 'Google Chrome', version: '{browser_version}'}},
                    {{brand: 'Chromium', version: '{browser_version}'}},
                    {{brand: 'Not=A?Brand', version: '99.0.0.0'}}
                ],
                model: '',
                platform: '{platform}',
                platformVersion: '{platform_version}',
                uaFullVersion: '{browser_version}',
                wow64: false
            }});
        }}
    }};
    if (!navigator.userAgentData) {{
        Object.defineProperty(navigator, 'userAgentData', {{
            get: () => fakeUAD,
            configurable: true,
            enumerable: true
        }});
    }} else {{
        try {{
            Object.defineProperty(navigator.userAgentData, 'platform', {{
                get: () => '{platform}', configurable: true
            }});
            Object.defineProperty(navigator.userAgentData, 'mobile', {{
                get: () => false, configurable: true
            }});
            navigator.userAgentData.getHighEntropyValues = function(hints) {{
                return fakeUAD.getHighEntropyValues(hints);
            }};
        }} catch(e) {{}}
    }}
}} catch(e) {{}}
}})();
"""


def get_all_scripts(profile: dict = None) -> str:
    """Combine all navigator spoofing into a single script.

    Args:
        profile: Optional fingerprint profile dict with keys like
                 'languages', 'hardware_concurrency', 'device_memory', 'os'.
    """
    if profile is None:
        profile = {}

    def _wrap(code):
        return f"""(function() {{
try {{
{code.strip()}
}} catch(e) {{ /* navigator sub-error silently caught */ }}
}})();"""

    scripts = [
        _wrap(REMOVE_WEBDRIVER),
        _wrap(FAKE_PLUGINS),
        _wrap(make_fake_languages(profile.get("languages", ["en-US", "en"]))),
        _wrap(make_fake_hardware(
            profile.get("hardware_concurrency", 4),
            profile.get("device_memory", 8),
        )),
        _wrap(FAKE_VENDOR),
    ]

    os_type = profile.get("os", "windows")
    if os_type == "windows":
        scripts.append(_wrap(FAKE_PLATFORM_WIN))
    elif os_type == "macos":
        scripts.append(_wrap(FAKE_PLATFORM_MAC))
    else:
        scripts.append(_wrap(FAKE_PLATFORM_LINUX))

    scripts.append(_wrap(FAKE_NOTIFICATIONS))
    scripts.append(_wrap(FAKE_PERMISSIONS))
    scripts.append(_wrap(FAKE_MEDIA_DEVICES))
    scripts.append(_wrap(FAKE_CONNECTION))

    # navigator.userAgentData for modern Client Hints detection
    scripts.append(_wrap(make_user_agent_data_script(
        os_type=os_type,
        browser_version=profile.get("browser_version", "126.0.0.0"),
    )))

    return "\n".join(scripts)
