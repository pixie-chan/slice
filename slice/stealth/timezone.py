"""Timezone and locale consistency."""


def make_script(timezone: str = "America/New_York", locale: str = "en-US"):
    """Generate timezone/locale spoofing scripts."""
    return f"""
;(function() {{
const _originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
Date.prototype.getTimezoneOffset = function() {{
    try {{
        const formatter = new Intl.DateTimeFormat('en-US', {{
            timeZone: '{timezone}',
            timeZoneName: 'shortOffset'
        }});
        const parts = formatter.formatToParts(this);
        const tzPart = parts.find(p => p.type === 'timeZoneName');
        if (tzPart) {{
            const match = tzPart.value.match(/GMT([+-]\\d+)?/);
            if (match) {{
                const hours = match[1] ? parseInt(match[1]) : 0;
                return -hours * 60;
            }}
        }}
    }} catch(e) {{}}
    return _originalGetTimezoneOffset.call(this);
}};

const _resolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
Intl.DateTimeFormat.prototype.resolvedOptions = function() {{
    const options = _resolvedOptions.call(this);
    options.timeZone = '{timezone}';
    options.locale = options.locale || '{locale}';
    return options;
}};
}})();
"""


def get_script(profile: dict = None) -> str:
    if profile is None:
        profile = {}
    return make_script(
        timezone=profile.get("timezone", "America/New_York"),
        locale=profile.get("locale", "en-US"),
    )
