"""Chrome API spoofing — chrome.runtime, chrome.app, chrome.csi, chrome.loadTimes."""

SCRIPT = """
try {
if (!window.chrome) {
    Object.defineProperty(window, 'chrome', {
        value: {},
        writable: true,
        configurable: true
    });
}

// chrome.runtime
window.chrome.runtime = {
    PlatformOs: {MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd'},
    PlatformArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
    PlatformNaclArch: {ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'},
    RequestUpdateCheckStatus: {THROTTLED: 'throttled', NO_UPDATE: 'no_update', UPDATE_AVAILABLE: 'update_available'},
    OnInstalledReason: {INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update', SHARED_MODULE_UPDATE: 'shared_module_update'},
    OnRestartRequiredReason: {APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic'},
    connect: function() {
        return {
            name: '',
            onMessage: {addListener: function() {}},
            postMessage: function() {},
            onDisconnect: {addListener: function() {}}
        };
    },
    sendMessage: function() {}
};

// chrome.app
window.chrome.app = {
    isInstalled: false,
    InstallState: {DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed'},
    RunningState: {CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running'},
    getDetails: function() { return null; },
    getIsInstalled: function() { return false; },
    runningState: function() { return 'cannot_run'; }
};

// chrome.csi
window.chrome.csi = function() {
    return {
        onloadT: Date.now(),
        startE: Date.now(),
        pageT: performance.now(),
        tran: 15
    };
};

// chrome.loadTimes
window.chrome.loadTimes = function() {
    const perf = performance.timing;
    return {
        commitLoadTime: perf.responseStart / 1000,
        connectionInfo: 'http/1.1',
        finishDocumentLoadTime: perf.domContentLoadedEventEnd / 1000,
        finishLoadTime: perf.loadEventEnd / 1000,
        firstPaintAfterLoadTime: 0,
        firstPaintTime: perf.responseEnd / 1000,
        navigationType: 'Other',
        npnNegotiatedProtocol: 'unknown',
        requestTime: perf.navigationStart / 1000,
        startLoadTime: perf.navigationStart / 1000,
        wasAlternateProtocolAvailable: false,
        wasFetchedViaSpdy: false,
        wasNpnNegotiated: false
    };
};
} catch(e) {}
"""


def get_script() -> str:
    return SCRIPT
