"""Stealth Browser — raw CDP browser automation with built-in stealth."""

from .browser import Browser, Tab
from .connection import CDPConnection, CDPError
from .stealth_browser import StealthBrowser, StealthPage
from .fingerprint.generator import generate_profile, load_profile, save_profile
from .fingerprint.validator import validate_profile
from .captcha.solver import CaptchaSolver
from .proxy.manager import ProxyManager

__all__ = [
    "Browser",
    "Tab",
    "CDPConnection",
    "CDPError",
    "StealthBrowser",
    "StealthPage",
    "generate_profile",
    "load_profile",
    "save_profile",
    "validate_profile",
    "CaptchaSolver",
    "ProxyManager",
]
