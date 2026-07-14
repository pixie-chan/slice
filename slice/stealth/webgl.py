"""WebGL fingerprint spoofing — vendor and renderer strings."""


def make_script(vendor: str = "Intel Inc.", renderer: str = "Intel Iris OpenGL Engine"):
    """Generate WebGL spoofing script for given vendor/renderer."""
    return f"""
;(function() {{
const _getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {{
    if (param === 37445) return '{vendor}';
    if (param === 37446) return '{renderer}';
    return _getParameter.call(this, param);
}};

if (typeof WebGL2RenderingContext !== 'undefined') {{
    const _getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(param) {{
        if (param === 37445) return '{vendor}';
        if (param === 37446) return '{renderer}';
        return _getParameter2.call(this, param);
    }};
}}
}})();
"""


def get_script(profile: dict = None) -> str:
    """Get WebGL spoofing script, optionally using a fingerprint profile."""
    if profile is None:
        profile = {}
    webgl = profile.get("webgl", {})
    return make_script(
        vendor=webgl.get("vendor", "Intel Inc."),
        renderer=webgl.get("renderer", "Intel Iris OpenGL Engine"),
    )
